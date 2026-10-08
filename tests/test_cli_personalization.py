from __future__ import annotations

from cli import build_parser
from sources.base import Paper
from storage.sqlite import PaperStore


def test_personalized_sort_parser_is_available():
    parser = build_parser()
    args = parser.parse_args(["list", "--sort", "personalized"])
    assert args.sort == "personalized"
    args = parser.parse_args(["top", "--sort", "personalized", "5"])
    assert args.sort == "personalized"
    assert args.limit == 5


def test_explicit_feedback_is_persistent(tmp_path):
    store = PaperStore(tmp_path / "db.sqlite3")
    try:
        paper_id = store.upsert_paper(
            Paper(source="fixture", title="A paper"),
            relevance_score=0.5,
            keyword_score=0.5,
            semantic_score=None,
            scoring_version="test",
            matched_groups={},
        )
        store.record_feedback(paper_id, 1.0, reason="useful")
        assert store.feedback_count() == 1
        rows = store.feedback_rows()
        assert rows[0]["explicit_feedback"] == 1.0
    finally:
        store.close()
