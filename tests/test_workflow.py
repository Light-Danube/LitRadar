from __future__ import annotations

from sources.base import Paper
from storage.sqlite import PaperStore


def make_paper(title: str = "Adaptive context for sarcasm") -> Paper:
    return Paper(
        source="fixture",
        title=title,
        abstract="Context-aware emotion and sarcasm analysis.",
        authors=["Test Author"],
        published_at="2026-01-01",
        venue="Test Venue",
        url="https://example.com/paper",
    )


def store_one(tmp_path):
    store = PaperStore(tmp_path / "library.sqlite3")
    paper_id = store.upsert_paper(
        make_paper(),
        relevance_score=0.9,
        keyword_score=0.8,
        semantic_score=0.95,
        scoring_version="test",
        matched_groups={"emotion": ["emotion analysis"]},
    )
    return store, paper_id


def test_workflow_status_persists(tmp_path):
    store, paper_id = store_one(tmp_path)
    store.set_status(paper_id, "to-read")
    store.add_tags(paper_id, ["sarcasm", "context"])
    store.set_notes(paper_id, "Read methodology.")

    row = store.get(paper_id)
    assert row["status"] == "to-read"
    assert "sarcasm" in row["tags_json"]
    assert row["notes"] == "Read methodology."

    store.set_status(paper_id, "dismissed", dismiss_reason="irrelevant")
    row = store.get(paper_id)
    assert row["status"] == "dismissed"
    assert row["dismiss_reason"] == "irrelevant"
    store.close()


def test_refresh_does_not_reset_workflow(tmp_path):
    store, paper_id = store_one(tmp_path)
    store.set_status(paper_id, "read")
    store.add_tags(paper_id, ["important"])
    store.set_notes(paper_id, "Keep for related work.")

    replacement = make_paper()
    replacement.abstract = "Refreshed abstract."
    store.upsert_paper(
        replacement,
        relevance_score=0.95,
        keyword_score=0.9,
        semantic_score=0.97,
        scoring_version="test-refresh",
        matched_groups={"adaptive_context": ["adaptive context"]},
    )
    row = store.get(paper_id)
    assert row["status"] == "read"
    assert "important" in row["tags_json"]
    assert row["notes"] == "Keep for related work."
    assert row["abstract"] == "Refreshed abstract."
    assert row["relevance_score"] == 0.95
    store.close()


def test_list_filters(tmp_path):
    store, first_id = store_one(tmp_path)
    second_id = store.upsert_paper(
        make_paper("Medical emotion recognition"),
        relevance_score=0.4,
        keyword_score=0.4,
        semantic_score=0.4,
        scoring_version="test",
        matched_groups={},
    )
    store.set_status(first_id, "to-read")
    store.add_tags(first_id, ["sarcasm"])

    assert [r["id"] for r in store.list_papers(status="to-read")] == [first_id]
    assert [r["id"] for r in store.list_papers(tag="sarcasm")] == [first_id]
    assert [r["id"] for r in store.list_papers(min_score=0.8)] == [first_id]
    assert {r["id"] for r in store.list_papers(query="Medical")} == {second_id}
    store.close()
