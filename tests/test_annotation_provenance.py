from __future__ import annotations

import sqlite3

import pytest

from sources.base import Paper
from storage.sqlite import PaperStore


@pytest.fixture
def library(tmp_path):
    store = PaperStore(tmp_path / "library.sqlite3")
    paper = Paper(source="fixture", title="Контекст і прагматика", doi="10.1234/provenance")
    paper_id = store.upsert_paper(paper, relevance_score=0.8, matched_groups={})
    yield store, paper_id, paper
    store.close()


def test_legacy_notes_are_backfilled_once_without_inventing_authorship(library):
    store, paper_id, _ = library
    # Simulate the pre-annotation database, retaining the existing notes field.
    store.conn.execute("UPDATE papers SET notes=? WHERE id=?", ("Стара нотатка", paper_id))
    store.conn.execute("DROP TABLE paper_annotations")
    store.conn.commit()
    path = store.path
    store.close()
    migrated = PaperStore(path)
    legacy = dict(migrated.list_annotations(paper_id, channel="research_note")[0])
    assert legacy["kind"] == "legacy"
    assert legacy["source_ref"] is None
    assert legacy["content"] == migrated.get(paper_id)["notes"] == "Стара нотатка"
    assert legacy["recorded_at"]
    migrated.close()
    reopened = PaperStore(path)
    assert [dict(row) for row in reopened.list_annotations(paper_id, channel="research_note")] == [legacy]
    reopened.close()


def test_notes_revisions_keep_legacy_search_and_export_field(library):
    store, paper_id, _ = library
    store.set_notes(paper_id, "Unusual provenance phrase")
    first = dict(store.list_annotations(paper_id, channel="research_note")[0])
    store.set_notes(paper_id, "Unusual provenance phrase")
    assert len(store.list_annotations(paper_id, channel="research_note")) == 1
    assert [row["id"] for row in store.list_papers(query="Unusual provenance")] == [paper_id]
    store.set_notes(paper_id, "Оновлена нотатка")
    store.set_notes(paper_id, "")
    history = store.list_annotations(paper_id, channel="research_note")
    assert [row["content"] for row in history] == ["", "Оновлена нотатка", first["content"]]
    assert all(row["kind"] == "user" for row in history)
    assert store.get(paper_id)["notes"] == ""
    assert store.list_papers(query="Unusual provenance") == []


def test_note_and_revision_roll_back_together(library):
    store, paper_id, _ = library
    store.set_notes(paper_id, "Original")
    store.conn.execute("CREATE TRIGGER reject_revision BEFORE INSERT ON paper_annotations "
                       "WHEN new.channel='research_note' BEGIN SELECT RAISE(ABORT, 'fixture failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        store.set_notes(paper_id, "Must roll back")
    assert store.get(paper_id)["notes"] == "Original"
    assert len(store.list_annotations(paper_id, channel="research_note")) == 1


def test_supplemental_origins_survive_refresh_without_replacing_notes(library):
    store, paper_id, paper = library
    store.set_notes(paper_id, "Personal interpretation")
    for kind in ("user", "imported", "extracted", "generated"):
        item = store.add_annotation(paper_id, "Матеріал: " + kind, kind=kind, source_ref="  DOI / page 3  ")
        assert item["kind"] == kind
        assert item["source_ref"] == "DOI / page 3"
        assert item["recorded_at"]
    paper.abstract = "Refreshed provider metadata"
    assert store.upsert_paper(paper, relevance_score=0.9, matched_groups={}) == paper_id
    assert store.get(paper_id)["notes"] == "Personal interpretation"
    assert len(store.list_annotations(paper_id)) == 4
    assert len(store.list_annotations(paper_id, channel="research_note")) == 1
    assert store.list_papers(query="Матеріал") == []  # Supplemental text does not enter personal-note search.


@pytest.mark.parametrize("kwargs", [
    {"content": " "}, {"content": "x" * 50_001}, {"content": "x", "kind": "legacy"},
    {"content": "x", "kind": "other"}, {"content": "x", "source_ref": "x" * 2001},
])
def test_annotation_validation(library, kwargs):
    store, paper_id, _ = library
    with pytest.raises(ValueError):
        store.add_annotation(paper_id, **kwargs)
    assert store.list_annotations(paper_id) == []


def test_missing_paper_and_foreign_key_cascade(library):
    store, paper_id, _ = library
    with pytest.raises(KeyError):
        store.add_annotation(999, "Unknown paper")
    with pytest.raises(KeyError):
        store.list_annotations(999)
    store.add_annotation(paper_id, "Supplement")
    store.set_notes(paper_id, "Notes")
    store.conn.execute("DELETE FROM papers WHERE id=?", (paper_id,))
    assert store.conn.execute("SELECT COUNT(*) FROM paper_annotations").fetchone()[0] == 0
