from __future__ import annotations

from pathlib import Path

from sources.base import Paper
from storage.sqlite import PaperStore


def _paper(title: str) -> Paper:
    return Paper(source="test", title=title, abstract="abstract")


def test_batch_upsert_persists_all_rows(tmp_path: Path):
    store = PaperStore(tmp_path / "batch.sqlite3")
    ids = store.upsert_papers(
        (
            _paper(f"Paper {i}"),
            i / 10,
            {},
            i / 10,
            None,
            "keyword-v0.1",
        )
        for i in range(1, 6)
    )
    assert len(ids) == 5
    assert len(store.list_papers(limit=10)) == 5
    store.close()


def test_indexes_exist_for_title_and_doi_lookup(tmp_path: Path):
    store = PaperStore(tmp_path / "indexes.sqlite3")
    names = {row[1] for row in store.conn.execute("PRAGMA index_list(papers)")}
    store.close()
    assert "idx_papers_title_normalized" in names
    assert "idx_papers_title_lower" in names
    assert "idx_papers_citations" in names
    assert "idx_papers_doi_lower" in names
