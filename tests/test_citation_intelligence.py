from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pytest

from config import RadarConfig
from sources import openalex, semantic_scholar
from sources.base import Paper
from storage.sqlite import PaperStore
from citation_intelligence import explore_citation_graph


def _paper(source: str, title: str, *, doi: str | None = None, external_id: str | None = None, identifiers=None, year="2024") -> Paper:
    return Paper(
        source=source,
        title=title,
        published_at=year,
        doi=doi,
        external_id=external_id,
        url=f"https://example.org/{title.casefold().replace(' ', '-')}",
        citation_count=7,
        identifiers=identifiers or {},
    )


def test_identifiers_link_cross_source_records_and_normalize_doi_arxiv(tmp_path: Path):
    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        paper_id = store.upsert_paper(
            _paper(
                "openalex", "A Shared Work", doi="https://doi.org/10.1234/AbC",
                external_id="https://openalex.org/W123", identifiers={"openalex_id": "https://openalex.org/W123"},
            ),
            relevance_score=0.4,
            matched_groups={},
        )
        duplicate_id = store.upsert_paper(
            _paper(
                "semantic_scholar", "A Shared Work", doi="10.1234/abc", external_id="S2-PAPER-ID",
                identifiers={"semantic_scholar_id": "S2-PAPER-ID", "openalex_id": "W123"},
            ),
            relevance_score=0.2,
            matched_groups={},
        )
        assert duplicate_id == paper_id
        identifiers = store.identifiers_for_paper(paper_id)
        assert identifiers["doi"] == ["10.1234/abc"]
        assert identifiers["openalex_id"] == ["w123"]
        assert identifiers["semantic_scholar_id"] == ["s2-paper-id"]
        assert openalex._openalex_short_id("w123") == "W123"

        arxiv_id = store.upsert_paper(
            _paper("arxiv", "arXiv source", external_id="2401.01234v2", identifiers={"arxiv_id": "2401.01234v2"}),
            relevance_score=0.0,
            matched_groups={},
        )
        linked_id = store.upsert_paper(
            _paper("semantic_scholar", "arXiv version", external_id="S2-ARXIV", identifiers={"arxiv_id": "2401.01234v3", "semantic_scholar_id": "S2-ARXIV"}),
            relevance_score=0.0,
            matched_groups={},
        )
        assert linked_id == arxiv_id
    finally:
        store.close()


def test_openalex_fetch_neighbors_covers_references_cited_by_and_related(monkeypatch):
    root = {
        "id": "https://openalex.org/W1",
        "display_name": "Root paper",
        "publication_date": "2024-01-01",
        "referenced_works": ["https://openalex.org/W2", "https://openalex.org/W3"],
        "related_works": ["https://openalex.org/W4"],
        "authorships": [],
    }
    candidates = {
        "https://openalex.org/W2": {"id": "https://openalex.org/W2", "display_name": "Prior work", "publication_date": "2020-01-01", "referenced_works": [], "authorships": []},
        "https://openalex.org/W3": {"id": "https://openalex.org/W3", "display_name": "Second prior", "publication_date": "2021-01-01", "referenced_works": [], "authorships": []},
        "https://openalex.org/W4": {"id": "https://openalex.org/W4", "display_name": "Related work", "publication_date": "2022-01-01", "referenced_works": [], "authorships": []},
        "https://openalex.org/W5": {"id": "https://openalex.org/W5", "display_name": "Citing work", "publication_date": "2025-01-01", "referenced_works": [], "authorships": []},
    }
    seen = []

    def fake_fetch(url, **kwargs):
        seen.append(url)
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if parsed.path.endswith("/W1"):
            return json.dumps(root).encode()
        filter_value = params.get("filter", [""])[0]
        if filter_value.startswith("openalex:"):
            ids = filter_value.removeprefix("openalex:").split("|")
            selected = [item for key, item in candidates.items() if key.rsplit("/", 1)[-1] in ids]
            return json.dumps({"results": selected}).encode()
        if filter_value == "cites:W1":
            return json.dumps({"results": [candidates["https://openalex.org/W5"]]}).encode()
        raise AssertionError(f"Unexpected OpenAlex request {url}")

    monkeypatch.setattr(openalex, "fetch_bytes", fake_fetch)
    assert [p.title for p in openalex.fetch_neighbors("W1", "references")] == ["Prior work", "Second prior"]
    assert [p.title for p in openalex.fetch_neighbors("W1", "cited-by")] == ["Citing work"]
    assert [p.title for p in openalex.fetch_neighbors("W1", "related")] == ["Related work"]
    assert len(seen) == 5  # direct OpenAlex ID avoids an extra seed fetch for cited-by


def test_semantic_scholar_fetch_neighbors_parses_directional_wrappers(monkeypatch):
    def fake_fetch(url, **kwargs):
        decoded = unquote(url)
        if "/references?" in decoded:
            return json.dumps({"data": [{"citedPaper": {"paperId": "S2-REF", "title": "Prior work", "year": 2019, "externalIds": {"DOI": "10.1/ref"}}}]}).encode()
        if "/citations?" in decoded:
            return json.dumps({"data": [{"citingPaper": {"paperId": "S2-CITING", "title": "Later work", "year": 2025}}]}).encode()
        raise AssertionError(url)

    monkeypatch.setattr(semantic_scholar, "fetch_bytes", fake_fetch)
    references = semantic_scholar.fetch_neighbors("S2-ROOT", "references", limit=10)
    cited_by = semantic_scholar.fetch_neighbors("S2-ROOT", "cited-by", limit=10)
    assert references[0].title == "Prior work"
    assert references[0].doi == "10.1/ref"
    assert references[0].identifiers["semantic_scholar_id"] == "S2-REF"
    assert cited_by[0].title == "Later work"


def test_bounded_graph_persists_correct_edge_directions_and_uses_cache(monkeypatch, tmp_path: Path):
    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        root_id = store.upsert_paper(
            _paper("openalex", "Seed paper", doi="10.1234/seed", external_id="https://openalex.org/W1", identifiers={"openalex_id": "W1"}),
            relevance_score=0.9,
            matched_groups={},
        )
        references = [_paper("openalex", "Prior paper", doi="10.1234/prior", external_id="https://openalex.org/W2", identifiers={"openalex_id": "W2"})]
        citing = [_paper("openalex", "Later paper", doi="10.1234/later", external_id="https://openalex.org/W3", identifiers={"openalex_id": "W3"})]
        calls = []

        def fake_openalex(identifier, direction, **kwargs):
            calls.append((identifier, direction))
            if direction == "references":
                return references
            if direction == "cited-by":
                return citing
            if direction == "related":
                return []
            raise AssertionError(direction)

        def fake_s2(identifier, direction, **kwargs):
            # Deliberately duplicate the same records from another source: identifier matching
            # should connect them to existing canonical papers rather than duplicate them.
            if direction == "references":
                return [_paper("semantic_scholar", "Prior paper", doi="10.1234/prior", external_id="S2-PRIOR", identifiers={"semantic_scholar_id": "S2-PRIOR"})]
            if direction == "cited-by":
                return []
            raise AssertionError(direction)

        monkeypatch.setattr(openalex, "fetch_neighbors", fake_openalex)
        monkeypatch.setattr(semantic_scholar, "fetch_neighbors", fake_s2)
        config = RadarConfig(source_timeout=1, source_retries=0, source_backoff=0, citation_cache_ttl=3600)
        first = explore_citation_graph(store, root_id, direction="both", depth=1, limit=10, max_nodes=10, config=config)
        assert {paper.title for paper in first.papers} == {"Prior paper", "Later paper"}
        assert store.relation_neighbors(root_id, "references")[0]["title"] == "Prior paper"
        assert store.relation_neighbors(root_id, "cited-by")[0]["title"] == "Later paper"
        assert store.citation_relation_count(root_id) == 2
        assert store.identifiers_for_paper(first.papers[0].paper_id)
        call_count = len(calls)

        def should_not_fetch(*args, **kwargs):
            raise AssertionError("fresh citation cache should avoid a provider request")

        monkeypatch.setattr(openalex, "fetch_neighbors", should_not_fetch)
        monkeypatch.setattr(semantic_scholar, "fetch_neighbors", should_not_fetch)
        second = explore_citation_graph(store, root_id, direction="both", depth=1, limit=10, max_nodes=10, config=config)
        assert second.cache_hits >= 2
        assert {paper.title for paper in second.papers} == {"Prior paper", "Later paper"}
        assert len(calls) == call_count
    finally:
        store.close()





def test_graph_degrees_are_limited_to_requested_subgraph(tmp_path: Path):
    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        ids = [
            store.upsert_paper(_paper("openalex", f"Degree node {number}", external_id=f"W{number + 171}"), relevance_score=0.0, matched_groups={})
            for number in range(3)
        ]
        store.record_relation(ids[0], ids[1], "cites", "openalex")
        store.record_relation(ids[0], ids[1], "cites", "semantic_scholar")
        store.record_relation(ids[1], ids[2], "cites", "openalex")
        assert store.relation_degrees_within(ids[:2]) == {ids[0]: 1, ids[1]: 1}
    finally:
        store.close()


def test_citation_cache_refetches_when_requested_limit_increases(tmp_path: Path):
    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        seed_id = store.upsert_paper(
            _paper("openalex", "Cache limit seed", external_id="W151"),
            relevance_score=0.0,
            matched_groups={},
        )
        store.record_citation_fetch(seed_id, "openalex", "references", 5, requested_limit=5)
        assert store.has_fresh_citation_fetch(seed_id, "openalex", "references", 3600, requested_limit=5)
        assert not store.has_fresh_citation_fetch(seed_id, "openalex", "references", 3600, requested_limit=20)
    finally:
        store.close()


def test_max_nodes_caps_stored_neighbors_and_edges(monkeypatch, tmp_path: Path):
    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        root_id = store.upsert_paper(
            _paper("openalex", "Bounded seed", external_id="https://openalex.org/W101", identifiers={"openalex_id": "W101"}),
            relevance_score=0.0,
            matched_groups={},
        )
        candidates = [
            _paper("openalex", f"Candidate {number}", doi=f"10.1234/candidate-{number}", external_id=f"https://openalex.org/W{number + 101}", identifiers={"openalex_id": f"W{number + 101}"})
            for number in range(3)
        ]
        monkeypatch.setattr(openalex, "fetch_neighbors", lambda identifier, direction, **kwargs: candidates if direction == "references" else [])
        config = RadarConfig(source_timeout=1, source_retries=0, source_backoff=0, citation_cache_ttl=3600)
        result = explore_citation_graph(store, root_id, direction="references", max_nodes=2, config=config)
        assert len(result.papers) == 1
        assert store.stats()["all"] == 2
        assert store.citation_relation_count(root_id) == 1
        assert result.warnings and "graph cap" in result.warnings[0]
    finally:
        store.close()


def test_related_edges_are_symmetric_and_self_edges_are_rejected(tmp_path: Path):
    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        a = store.upsert_paper(_paper("openalex", "A", external_id="W11"), relevance_score=0, matched_groups={})
        b = store.upsert_paper(_paper("openalex", "B", external_id="W12"), relevance_score=0, matched_groups={})
        assert store.record_relation(a, b, "related", "openalex") is True
        assert store.record_relation(b, a, "related", "openalex") is False
        assert store.record_relation(a, a, "related", "openalex") is False
        assert store.relation_neighbors(a, "related")[0]["id"] == b
        assert store.relation_neighbors(b, "related")[0]["id"] == a
    finally:
        store.close()


def test_graph_bounds_are_validated(tmp_path: Path):
    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        paper_id = store.upsert_paper(_paper("openalex", "Seed", external_id="W21"), relevance_score=0, matched_groups={})
        with pytest.raises(ValueError, match="depth"):
            explore_citation_graph(store, paper_id, depth=0)
        with pytest.raises(ValueError, match="limit"):
            explore_citation_graph(store, paper_id, limit=101)
        with pytest.raises(ValueError, match="max_nodes"):
            explore_citation_graph(store, paper_id, max_nodes=201)
    finally:
        store.close()


def test_two_different_explicit_dois_with_same_title_are_not_merged(tmp_path: Path):
    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        first = store.upsert_paper(
            _paper("openalex", "Identical title", doi="10.1111/one", external_id="W31"),
            relevance_score=0,
            matched_groups={},
        )
        second = store.upsert_paper(
            _paper("semantic_scholar", "Identical title", doi="10.1111/two", external_id="S2-TWO"),
            relevance_score=0,
            matched_groups={},
        )
        assert first != second
        assert store.stats()["all"] == 2
    finally:
        store.close()


def test_cli_explore_command_is_discoverable_and_bounded():
    from cli import build_parser

    args = build_parser().parse_args([
        "--db", "test.sqlite3", "explore", "17", "--direction", "all", "--depth", "2",
        "--limit", "10", "--max-nodes", "40", "--refresh",
    ])
    assert args.command == "explore"
    assert args.paper_id == 17
    assert args.direction == "all"
    assert args.depth == 2
    assert args.limit == 10
    assert args.max_nodes == 40
    assert args.refresh is True


def test_citation_cache_ttl_is_configurable(monkeypatch):
    monkeypatch.setenv("LITRADAR_CITATION_CACHE_TTL", "120")
    config = RadarConfig.load()
    assert config.citation_cache_ttl == 120
    assert config.masked_dict()["citation_cache_ttl"] == 120
