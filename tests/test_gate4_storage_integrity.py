"""Synthetic identity refreshes and real SQLite transaction failures only."""
from contextlib import closing
import sqlite3

import pytest

from sources.base import Paper
from storage.evidence import EvidenceStore
from storage.sqlite import PaperStore
from storage.venue_presets import VenuePresetStore


MANUAL_COLUMNS = ("id", "notes", "tags_json", "status", "dismiss_reason", "created_at",
                  "read_at", "archived_at", "dismissed_at", "llm_assessment_json")


def upsert(store, paper):
    return store.upsert_paper(paper, relevance_score=.8, matched_groups={"synthetic": ["refresh"]})


def batch_row(paper):
    return paper, .8, {}, .8, None, "keyword-v0.1"


def durable_rows(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        rows = {}
        for (name,) in conn.execute("SELECT name FROM sqlite_schema WHERE type='table'"):
            if name.startswith("papers_fts"):
                continue  # Derived index, not authoritative user state.
            quoted = '"' + name.replace('"', '""') + '"'
            count = len(conn.execute(f"PRAGMA table_info({quoted})").fetchall())
            order = ",".join(str(index) for index in range(1, count + 1))
            rows[name] = conn.execute(f"SELECT * FROM {quoted} ORDER BY {order}").fetchall()
        return rows


def manual_state(path):
    rows = durable_rows(path)
    rows.pop("papers")
    rows.pop("paper_identifiers")  # Provider observations/last-seen may refresh.
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
        rows["manual_paper_fields"] = conn.execute(
            "SELECT " + ",".join(MANUAL_COLUMNS) + " FROM papers ORDER BY id").fetchall()
    return rows


@pytest.fixture
def library(tmp_path):
    path = tmp_path / "synthetic.sqlite3"
    store = PaperStore(path)
    try:
        one = upsert(store, Paper(source="openalex", external_id="W1", doi="10.1000/first",
                                  title="Synthetic first", abstract="Original abstract"))
        two = upsert(store, Paper(source="openalex", external_id="W2", doi="10.1000/second",
                                  title="Synthetic second"))
        store.set_notes(one, "First synthetic note")
        store.set_notes(one, "Reviewed synthetic note Україна")
        store.set_tags(one, ["manual", "українська"])
        store.set_status(one, "read")
        store.set_status(two, "dismissed", dismiss_reason="Manual synthetic decision")
        store.set_llm_assessment(one, {"summary": "Saved synthetic assessment; no model"})
        store.record_relation(one, two, "cites", "fixture")
        store.record_feedback(one, 1, reason="Synthetic reviewed feedback")
        note = store.add_annotation(one, "Synthetic supplement", kind="imported", source_ref="fixture")
        store.edit_annotation(one, note["id"], expected_revision=1,
                              content="Revised synthetic supplement", review_status="accepted")
        store.change_annotation_recovery(one, note["id"], expected_revision=2, delete=True)
        evidence = EvidenceStore(store)
        evidence.update(one, {"method": {"value": "Synthetic method", "origin": "user"}})
        evidence.update(one, {"method": {"value": "Reviewed method", "origin": "user"}}, expected_revision=1)
        presets = VenuePresetStore(store)
        removed = presets.list()[0]
        presets.delete(removed["id"], removed["revision"])
    finally:
        store.close()
    return path, one, two


def test_provider_id_refresh_preserves_manual_history_tombstones_and_relations(library):
    path, one, _ = library
    before = manual_state(path)
    store = PaperStore(path)
    try:
        assert upsert(store, Paper(source="openalex", external_id="W1", title="Refreshed provider title",
                                   abstract="Refreshed provider abstract", citation_count=12)) == one
    finally:
        store.close()
    reopened = PaperStore(path)
    try:
        assert reopened.total_count() == 2
        assert reopened.get(one)["abstract"] == "Refreshed provider abstract"
        assert reopened.get(one)["doi_normalized"] == "10.1000/first"
        assert reopened.identifiers_for_paper(one)["openalex_id"] == ["w1"]
        assert len(VenuePresetStore(reopened).list()) == 2
    finally:
        reopened.close()
    assert manual_state(path) == before


def test_normalized_doi_cross_provider_refresh_keeps_canonical_source_identity(library):
    path, one, _ = library
    before = manual_state(path)
    store = PaperStore(path)
    try:
        assert upsert(store, Paper(source="semantic_scholar", external_id="SS1",
                                   doi="https://doi.org/10.1000/FIRST", title="Cross-provider refresh")) == one
    finally:
        store.close()
    reopened = PaperStore(path)
    try:
        row = reopened.get(one)
        assert (row["source"], row["external_id"]) == ("openalex", "W1")
        assert reopened.identifiers_for_paper(one) == {
            "doi": ["10.1000/first"], "openalex_id": ["w1"], "semantic_scholar_id": ["ss1"]}
        assert reopened.total_count() == 2
    finally:
        reopened.close()
    assert manual_state(path) == before


def test_conflicting_existing_doi_and_provider_alias_roll_back_entire_batch(library):
    path, _, _ = library
    before = durable_rows(path)
    store = PaperStore(path)
    try:
        with pytest.raises(ValueError, match="Conflicting"):
            store.upsert_papers([
                batch_row(Paper(source="fixture", external_id="new", doi="10.1000/new", title="Uncommitted new paper")),
                batch_row(Paper(source="openalex", external_id="W2", doi="10.1000/first", title="Contradictory identities")),
            ])
    finally:
        store.close()
    reopened = PaperStore(path)
    reopened.close()
    assert durable_rows(path) == before


def test_malformed_second_metadata_row_rolls_back_prior_refresh(library):
    path, _, _ = library
    before = durable_rows(path)
    store = PaperStore(path)
    try:
        with pytest.raises(ValueError):
            store.upsert_papers([
                batch_row(Paper(source="openalex", external_id="W1", title="Uncommitted refresh")),
                batch_row(Paper(source="fixture", title="Malformed count", citation_count="not-an-integer")),
            ])
    finally:
        store.close()
    reopened = PaperStore(path)
    reopened.close()
    assert durable_rows(path) == before


def test_real_sqlite_writer_lock_preserves_rows_and_allows_explicit_retry(library):
    path, one, _ = library
    before, manual_before = durable_rows(path), manual_state(path)
    store = PaperStore(path)
    store.conn.execute("PRAGMA busy_timeout=0")
    with closing(sqlite3.connect(path)) as locker:
        try:
            locker.execute("BEGIN IMMEDIATE")
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                upsert(store, Paper(source="openalex", external_id="W1", title="Retryable metadata refresh"))
            assert durable_rows(path) == before
            locker.rollback()
            assert upsert(store, Paper(source="openalex", external_id="W1", title="Retryable metadata refresh")) == one
        finally:
            locker.rollback()
            store.close()
    reopened = PaperStore(path)
    try:
        assert reopened.get(one)["title"] == "Retryable metadata refresh"
        assert reopened.total_count() == 2
    finally:
        reopened.close()
    assert manual_state(path) == manual_before
