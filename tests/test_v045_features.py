from __future__ import annotations

import json
from pathlib import Path

from sources.base import Paper
from storage.sqlite import PaperStore


def add(store: PaperStore, paper: Paper) -> int:
    return store.upsert_paper(
        paper, relevance_score=0.7, keyword_score=0.7, semantic_score=0.7,
        scoring_version="test", matched_groups={},
    )


def test_title_hash_dedup_ignores_punctuation_and_case(tmp_path: Path):
    store = PaperStore(tmp_path / "db.sqlite3")
    first = add(store, Paper(source="a", title="Context-Aware Emotion Analysis!"))
    second = add(store, Paper(source="b", title="context aware emotion analysis"))
    assert first == second
    assert store.total_count() == 1
    store.close()


def test_cross_source_dedup_merges_source_refs_and_keeps_manual_workflow(tmp_path: Path):
    store = PaperStore(tmp_path / "db.sqlite3")
    first = add(
        store,
        Paper(source="arxiv", title="Adaptive Context", external_id="https://arxiv.org/abs/2501.12345", source_tags=["cs.CL"], identifiers={"arxiv_id": "2501.12345"}),
    )
    store.set_status(first, "to-read")
    store.add_tags(first, ["important"])

    second = add(
        store,
        Paper(source="semantic_scholar", title="Adaptive Context", doi="10.1234/example", source_tags=["Computer Science"], identifiers={"semantic_scholar_id": "S2-1", "arxiv_id": "2501.12345"}),
    )
    row = store.get(first)
    assert second == first
    assert row["status"] == "to-read"
    assert "important" in json.loads(row["tags_json"])
    assert set(json.loads(row["source_tags_json"])) == {"Computer Science", "cs.CL"}
    refs = json.loads(row["source_refs_json"])
    assert set(refs) >= {"arxiv", "semantic_scholar"}
    assert row["external_id"] == "https://arxiv.org/abs/2501.12345"
    assert store.total_count() == 1
    store.close()


def test_source_tags_participate_in_filter_and_tag_listing(tmp_path: Path):
    store = PaperStore(tmp_path / "db.sqlite3")
    paper_id = add(store, Paper(source="arxiv", title="Emotion", source_tags=["cs.CL", "NLP"]))
    assert [row["id"] for row in store.list_papers(tag="cs.CL")] == [paper_id]
    assert "cs.CL" in store.all_tags()
    store.close()


def test_cli_list_reports_total_count(tmp_path: Path):
    # Smoke-test via direct store behavior; CLI formatting is covered by parser/integration tests.
    store = PaperStore(tmp_path / "db.sqlite3")
    for index in range(3):
        add(store, Paper(source="fixture", title=f"Paper {index}"))
    assert store.total_count() == 3
    store.set_status(1, "read")
    assert store.total_count(status="read") == 1
    assert len(store.list_papers(limit=2)) == 2
    store.close()
