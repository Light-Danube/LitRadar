from pathlib import Path

import pytest

from sources.base import Paper
from storage.sqlite import PaperStore


def test_full_text_search_indexes_title_abstract_and_notes(tmp_path: Path):
    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        paper_id = store.upsert_paper(
            Paper(
                source="test",
                title="A Study of Conversational Context",
                abstract="We propose selective context attribution for sarcasm detection.",
                authors=["Jane Doe"],
                venue="NLP Workshop",
            ),
            relevance_score=0.8,
            matched_groups={"context": ["context attribution"]},
        )
        store.set_notes(paper_id, "Potential baseline for my dissertation literature review.")
        if not store.fts_available:
            pytest.skip("SQLite build has no FTS5; LIKE fallback is exercised instead")

        assert [row["id"] for row in store.list_papers(query="context attribution")] == [paper_id]
        assert [row["id"] for row in store.list_papers(query="dissertation literature")] == [paper_id]
        assert store.total_count(query="dissertation literature") == 1
        assert store.total_count(query="phrase-with-no-match") == 0

        store.set_notes(paper_id, "Revised note about context selection.")
        assert [row["id"] for row in store.list_papers(query="context selection")] == [paper_id]
        assert store.list_papers(query="dissertation literature") == []
    finally:
        store.close()


def test_search_fallback_includes_notes_when_fts_unavailable(tmp_path: Path, monkeypatch):
    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        paper_id = store.upsert_paper(
            Paper(source="test", title="A paper", abstract="", authors=[]),
            relevance_score=0.5,
            matched_groups={},
        )
        store.set_notes(paper_id, "Need to cite this in the related work chapter.")
        monkeypatch.setattr(store, "fts_available", False)
        assert [row["id"] for row in store.list_papers(query="related work")] == [paper_id]
        assert store.total_count(query="related work") == 1
    finally:
        store.close()
