from __future__ import annotations

import json
from pathlib import Path

from sources.base import Paper
from storage.sqlite import PaperStore


def make_store(tmp_path: Path) -> PaperStore:
    return PaperStore(tmp_path / "library.sqlite3")


def add(store: PaperStore, title: str, published_at: str, citations: int, score: float) -> int:
    return store.upsert_paper(
        Paper(
            source="test",
            title=title,
            abstract="context emotion sarcasm",
            published_at=published_at,
            citation_count=citations,
        ),
        relevance_score=score,
        keyword_score=score,
        semantic_score=score,
        scoring_version="test",
        matched_groups={},
    )


def test_sort_options(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    old_id = add(store, "Zeta", "2024-01-01", 100, 0.7)
    new_id = add(store, "Alpha", "2026-01-01", 20, 0.8)

    assert [r["id"] for r in store.list_papers(sort="recent")] == [new_id, old_id]
    assert [r["id"] for r in store.list_papers(sort="published_oldest")] == [old_id, new_id]
    assert [r["id"] for r in store.list_papers(sort="title")] == [new_id, old_id]
    assert [r["id"] for r in store.list_papers(sort="citations")] == [old_id, new_id]
    store.close()


def test_tags_can_be_added_removed_and_replaced(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    paper_id = add(store, "Tagged", "2026-01-01", 1, 0.5)

    store.add_tags(paper_id, ["sarcasm", "Context"])
    assert json.loads(store.get(paper_id)["tags_json"]) == ["Context", "sarcasm"]

    store.remove_tags(paper_id, ["context"])
    assert json.loads(store.get(paper_id)["tags_json"]) == ["sarcasm"]

    store.set_tags(paper_id, ["research", "important", "research"])
    assert json.loads(store.get(paper_id)["tags_json"]) == ["important", "research"]
    assert store.all_tags() == ["important", "research"]
    assert [r["id"] for r in store.list_papers(tag="research")] == [paper_id]
    assert [r["id"] for r in store.list_papers(tag="search")] == []
    assert store.total_count(tag="research") == 1
    assert store.total_count(tag="search") == 0
    store.close()
