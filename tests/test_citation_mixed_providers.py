"""Synthetic provider responses exercise ingestion, not merely stored-edge fixtures."""
from __future__ import annotations

import pytest

from citation_intelligence import explore_citation_graph
from config import RadarConfig
from sources import openalex, semantic_scholar
from sources.base import Paper
from storage.sqlite import PaperStore


def record(provider, name):
    number = {"seed": 1, "peer": 2, "distant": 3}[name]
    return Paper(
        source=provider, title=f"Synthetic {name}",
        doi=f"https://doi.org/10.1234/{name.upper()}" if provider == "openalex" else f"10.1234/{name}",
        external_id=f"https://openalex.org/W{number}" if provider == "openalex" else f"S2-{name}",
        identifiers={"openalex_id": f"W{number}"} if provider == "openalex" else {"semantic_scholar_id": f"S2-{name}"},
        published_at="2024",
    )


@pytest.mark.parametrize("initial_provider", ["openalex", "semantic_scholar"])
def test_mixed_aliases_keep_antiparallel_cycles_without_duplicate_or_self_edges(tmp_path, monkeypatch, initial_provider):
    store = PaperStore(tmp_path / "synthetic.sqlite3")
    try:
        seed = store.upsert_paper(record(initial_provider, "seed"), relevance_score=.7, matched_groups={})
        calls = []

        def response(provider, identifier, direction, **kwargs):
            calls.append((provider, identifier, direction))
            name = "peer" if "peer" in identifier.lower() or identifier.lower() == "w2" else "seed"
            other = "seed" if name == "peer" else "peer"
            # Both providers report both directions; repeated wrappers and a self
            # record must not merge reverse citations or create duplicate papers.
            if direction in {"references", "cited-by"}:
                candidates = [record(provider, other), record(provider, other), record(provider, name)]
                if name == "peer" and direction == "references":
                    candidates.append(record(provider, "distant"))
                return candidates
            return [record(provider, other), record(provider, other)]

        monkeypatch.setattr(openalex, "fetch_neighbors", lambda identifier, direction, **kw: response("openalex", identifier, direction, **kw))
        monkeypatch.setattr(semantic_scholar, "fetch_neighbors", lambda identifier, direction, **kw: response("semantic_scholar", identifier, direction, **kw))
        config = RadarConfig(source_timeout=1, source_retries=0, source_backoff=0, citation_cache_ttl=3600)
        result = explore_citation_graph(store, seed, direction="all", depth=2, max_nodes=10, config=config)
        assert not result.errors
        assert store.stats()["all"] == 3
        peer = next(p.paper_id for p in result.papers if p.title == "Synthetic peer")
        distant = next(p.paper_id for p in result.papers if p.title == "Synthetic distant")
        rows = store.conn.execute("SELECT source_paper_id,target_paper_id,relation_type,provider FROM paper_relations").fetchall()
        actual = {tuple(row) for row in rows}
        expected = {(a, b, "cites", provider) for a, b in [(seed, peer), (peer, seed), (peer, distant)] for provider in ["openalex", "semantic_scholar"]}
        expected.add((min(seed, peer), max(seed, peer), "related", "openalex"))
        assert actual == expected
        assert len(rows) == len(actual)
        assert all(a != b for a, b, _, _ in actual)
        assert store.identifiers_for_paper(peer)["semantic_scholar_id"] == ["s2-peer"]
        assert {p.depth for p in result.papers if p.paper_id == distant} == {2}

        before = len(calls)
        cached = explore_citation_graph(store, seed, direction="all", depth=2, max_nodes=10, config=config)
        assert len(calls) == before and cached.cache_hits > 0
        refreshed = explore_citation_graph(store, seed, direction="all", depth=2, max_nodes=10, config=config, refresh=True)
        assert len(calls) > before and refreshed.edges_added == 0
        assert store.stats()["all"] == 3
        assert {tuple(row) for row in store.conn.execute("SELECT source_paper_id,target_paper_id,relation_type,provider FROM paper_relations")} == expected
    finally:
        store.close()
