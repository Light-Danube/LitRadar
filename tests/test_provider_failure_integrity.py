"""Provider outages use fake transports and preserve disposable local libraries."""
from __future__ import annotations

from contextlib import closing
import io
import json
import socket
import sqlite3
import ssl
from types import SimpleNamespace
import urllib.error

import pytest

import pipeline
import research_digest
from config import RadarConfig
from sources.base import Paper
from sources import http, registry
from storage.evidence import EvidenceStore
from storage.sqlite import PaperStore
from storage.venue_presets import VenuePresetStore


POISON = "PRIVATE_PROVIDER_REASON_DO_NOT_DISPLAY"
KEY = "synthetic-api-key-never-real"
URL = f"https://synthetic.invalid/private?api_key={KEY}&query={POISON}"
FAILURES = [403, 404, 429, 503, "timeout", "offline"]


def provider_error(kind):
    if isinstance(kind, int):
        return urllib.error.HTTPError(URL, kind, f"{POISON} {KEY}", {}, io.BytesIO(POISON.encode()))
    if kind == "timeout":
        return TimeoutError(f"{POISON} {URL}")
    return urllib.error.URLError(f"{POISON} {URL}")


def assert_safe(value):
    text = str(value)
    assert POISON not in text
    assert KEY not in text
    assert "synthetic.invalid" not in text


@pytest.mark.parametrize("kind", [400, 401, 403, 404, 429, 500, 503, 418,
                                  "timeout", "offline", "json", "unicode", "dns", "tls", "wrapped-timeout", "custom"])
def test_provider_diagnostics_are_bounded_and_omit_private_exception_content(kind):
    error = provider_error(kind)
    if kind == "json":
        error = json.JSONDecodeError(POISON, f"{POISON} {URL}", 0)
    elif kind == "unicode":
        error = UnicodeError(f"{POISON} {URL}")
    elif kind == "dns":
        error = urllib.error.URLError(socket.gaierror(f"{POISON} {URL}"))
    elif kind == "tls":
        error = urllib.error.URLError(ssl.SSLError(f"{POISON} {URL}"))
    elif kind == "wrapped-timeout":
        error = urllib.error.URLError(TimeoutError(f"{POISON} {URL}"))
    elif kind == "custom":
        error = type(POISON, (Exception,), {})(f"{POISON} {URL}")
    message = http.format_provider_error(error)
    assert 20 < len(message) < 300
    assert_safe(message)
    if isinstance(kind, int):
        assert str(kind) in message
        assert error.fp.tell() == 0, "Formatting must not read provider response bodies"


@pytest.fixture(autouse=True)
def isolated_providers(monkeypatch):
    # Never consult .env or the ordinary provider cache, even on a developer's machine.
    config = RadarConfig(enabled_sources=("openalex", "semantic_scholar"), source_cache_ttl=0,
                         source_workers=2, source_retries=0, source_backoff=0)
    monkeypatch.setattr(RadarConfig, "load", classmethod(lambda cls: config))
    monkeypatch.setattr(registry, "load_cached", lambda *args, **kwargs: None)
    monkeypatch.setattr(registry, "save_cached", lambda *args, **kwargs: None)
    monkeypatch.setattr(http.urllib.request, "urlopen", lambda *args, **kwargs: pytest.fail("Unexpected external request"))


def durable_rows(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
        result = {}
        for (name,) in connection.execute("SELECT name FROM sqlite_schema WHERE type='table'"):
            if name.startswith("papers_fts"):
                continue  # Derived search index, not authoritative user content.
            quoted = '"' + name.replace('"', '""') + '"'
            columns = len(connection.execute(f"PRAGMA table_info({quoted})").fetchall())
            order = ",".join(str(index) for index in range(1, columns + 1))
            result[name] = connection.execute(f"SELECT * FROM {quoted} ORDER BY {order}").fetchall()
        return result


@pytest.fixture
def library(tmp_path):
    database, profile = tmp_path / "synthetic.sqlite3", tmp_path / "profile.json"
    profile.write_text(json.dumps({"name": "Synthetic only", "groups": [
        {"name": "context", "weight": 1, "terms": ["context"]}],
        "ranking": {"keyword_weight": 1, "semantic_weight": 0}}), encoding="utf-8")
    store = PaperStore(database)
    try:
        paper_id = store.upsert_paper(Paper(source="openalex", external_id="existing",
                                           title="Synthetic context paper", doi="10.1000/provider-fixture"),
                                      relevance_score=0.5, matched_groups={})
        other_id = store.upsert_paper(Paper(source="fixture", external_id="other", title="Synthetic related paper"),
                                      relevance_score=0.2, matched_groups={})
        store.set_notes(paper_id, "Original synthetic manual note")
        store.set_notes(paper_id, "Revised synthetic manual note Україна")
        store.set_tags(paper_id, ["manual", "українська"])
        store.set_status(paper_id, "read")
        store.set_status(other_id, "dismissed", dismiss_reason="Synthetic manual decision")
        store.record_relation(paper_id, other_id, "cites", "fixture")
        store.record_feedback(paper_id, 1, reason="Synthetic user feedback")
        annotation = store.add_annotation(paper_id, "Synthetic annotation")
        store.edit_annotation(paper_id, annotation["id"], expected_revision=1,
                              content="Revised synthetic annotation", review_status="accepted")
        store.change_annotation_recovery(paper_id, annotation["id"], expected_revision=2, delete=True)
        evidence = EvidenceStore(store)
        evidence.update(paper_id, {"method": {"value": "Synthetic method", "origin": "user"}})
        worksheet = evidence.update(paper_id, {"method": {"value": "Reviewed method", "origin": "user"}}, expected_revision=1)
        presets = VenuePresetStore(store)
        deleted = presets.list()[0]
        presets.delete(deleted["id"], deleted["revision"])
    finally:
        store.close()
    return SimpleNamespace(database=database, profile=profile, paper_id=paper_id, other_id=other_id, worksheet=worksheet)


def configure_registry(monkeypatch, kind, *, papers=None):
    def fail(*args):
        raise provider_error(kind)
    good_or_bad = fail if papers is None else lambda *args: papers
    selected = registry.SourceRegistry([registry.SourceDefinition("openalex", good_or_bad),
                                        registry.SourceDefinition("semantic_scholar", fail)])
    monkeypatch.setattr(registry, "default_registry", lambda: selected)


def local_web_remains_usable(library, tmp_path, monkeypatch):
    pytest.importorskip("fastapi", reason="optional local workspace dependency")
    pytest.importorskip("httpx", reason="optional TestClient dependency")
    from fastapi.testclient import TestClient
    import workspace_web

    monkeypatch.setattr(workspace_web, "ensure_user_defaults", lambda: None)
    def app():
        return workspace_web.create_app(library.database, semantic_enabled=False,
                                        research_results_root=tmp_path / "research")
    with TestClient(app()) as client:
        assert client.get("/api/health").json()["ok"] is True
        assert client.get("/api/papers").status_code == 200
        paper = client.get(f"/api/papers/{library.paper_id}").json()
        assert paper["notes"] == "Revised synthetic manual note Україна"
        assert paper["status"] == "read" and set(paper["tags"]) == {"manual", "українська"}
        assert client.get(f"/api/papers/{library.paper_id}/evidence").json() == library.worksheet
        response = client.patch(f"/api/papers/{library.paper_id}", json={"notes": "Edited offline after provider outage"})
        assert response.status_code == 200
        exported = client.post("/api/research/exports", json={"paper_ids": [library.paper_id], "identifier": "offline-export"})
        assert exported.status_code == 200
        markdown = client.get("/api/research/artifacts/offline-export/matrix.md")
        assert markdown.status_code == 200 and "Reviewed method" in markdown.text
        csv = client.get("/api/research/artifacts/offline-export/matrix.csv")
        assert csv.status_code == 200 and "Reviewed method" in csv.text
    with TestClient(app()) as client:
        assert client.get(f"/api/papers/{library.paper_id}").json()["notes"] == "Edited offline after provider outage"
        assert client.get(f"/api/papers/{library.paper_id}/evidence").json() == library.worksheet


@pytest.mark.parametrize("kind", FAILURES)
def test_all_provider_failures_leave_durable_rows_unchanged_and_local_web_works(library, tmp_path, monkeypatch, kind):
    configure_registry(monkeypatch, kind)
    before, events = durable_rows(library.database), []
    summary, ranked = pipeline.search_and_ingest("context fixture", db_path=library.database,
        profile_path=library.profile, semantic=False, progress=lambda *event: events.append(event))
    assert summary.fetched == 0 and summary.newly_stored == 0 and summary.library_total == 2
    assert ranked == [] and set(summary.source_errors) == {"openalex", "semantic_scholar"}
    assert len([event for event in events if event[0] == "error"]) == 2
    assert_safe(summary.source_errors)
    assert_safe(events)
    assert durable_rows(library.database) == before
    local_web_remains_usable(library, tmp_path, monkeypatch)


def test_partial_provider_success_ingests_results_and_preserves_manual_state(library, tmp_path, monkeypatch):
    papers = [Paper(source="openalex", external_id="existing", title="Synthetic context paper",
                    doi="10.1000/provider-fixture", abstract="Updated provider metadata"),
              Paper(source="openalex", external_id="new", title="New synthetic context discovery")]
    configure_registry(monkeypatch, 503, papers=papers)
    before = durable_rows(library.database)
    summary, ranked = pipeline.search_and_ingest("context fixture", db_path=library.database,
        profile_path=library.profile, semantic=False)
    assert summary.fetched == 2 and summary.newly_stored == 1 and summary.library_total == 3
    assert summary.source_results == {"openalex": 2, "semantic_scholar": 0}
    assert len(ranked) == 2 and set(summary.source_errors) == {"semantic_scholar"}
    assert_safe(summary.source_errors)
    after = durable_rows(library.database)
    assert next(row for row in after["papers"] if row[0] == library.other_id) == next(
        row for row in before["papers"] if row[0] == library.other_id)
    # Successful metadata refresh/identity registration may change; user histories may not.
    for table in ("feedback_events", "paper_relations", "paper_annotations", "annotation_revisions",
                  "evidence_worksheets", "evidence_worksheet_revisions", "research_venue_presets"):
        assert after[table] == before[table]
    local_web_remains_usable(library, tmp_path, monkeypatch)


@pytest.mark.parametrize("kind", [403, "offline"])
def test_scheduled_failures_only_add_explicit_safe_run_history(library, tmp_path, monkeypatch, kind):
    configure_registry(monkeypatch, kind)
    config = tmp_path / "scan.json"
    config.write_text(json.dumps({"queries": [{"name": "Fixture topic", "query": "context fixture",
        "sources": ["openalex", "semantic_scholar"]}], "scan": {"semantic": False}}), encoding="utf-8")
    before, events = durable_rows(library.database), []
    result = research_digest.run_scheduled_scan(db_path=library.database, profile_path=library.profile,
        config_path=config, semantic=False, progress=lambda *event: events.append(event))
    assert result.fetched == 0 and result.newly_stored == 0 and result.library_total == 2
    assert len(result.errors) == 2
    assert_safe(result.errors)
    assert_safe(events)
    after = durable_rows(library.database)
    for table in before:
        if table not in {"research_runs", "sqlite_sequence"}:
            assert after[table] == before[table]
    assert {n: v for n, v in after["sqlite_sequence"] if n != "research_runs"} == dict(before["sqlite_sequence"])
    assert len(after["research_runs"]) == len(before["research_runs"]) + 1
    with closing(sqlite3.connect(library.database)) as connection:
        error, payload = connection.execute("SELECT error_message,summary_json FROM research_runs WHERE id=?", (result.run_id,)).fetchone()
        assert error and json.loads(payload)["errors"]
        assert_safe(error)
        assert_safe(payload)


def test_unexpected_scan_failure_persists_only_safe_explicit_run_record(library, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError(f"{POISON} {URL}")
    monkeypatch.setattr(research_digest, "search_and_ingest", fail)
    config = tmp_path / "scan.json"
    config.write_text(json.dumps({"queries": ["context fixture"]}), encoding="utf-8")
    before, events = durable_rows(library.database), []
    result = research_digest.run_scheduled_scan(db_path=library.database, profile_path=library.profile,
        config_path=config, semantic=False, progress=lambda *event: events.append(event))
    assert result.errors and result.fetched == 0 and result.newly_stored == 0
    assert_safe(result.errors)
    assert_safe(events)
    after = durable_rows(library.database)
    for table in before:
        if table not in {"research_runs", "sqlite_sequence"}:
            assert after[table] == before[table]
    assert len(after["research_runs"]) == len(before["research_runs"]) + 1
    assert_safe(after["research_runs"])


def test_failed_citation_fetches_preserve_library_and_persist_safe_errors(library, monkeypatch):
    import citation_intelligence

    def fail(*args, **kwargs):
        raise urllib.error.HTTPError(URL, 403, POISON, {}, io.BytesIO(POISON.encode()))
    monkeypatch.setattr(citation_intelligence, "_fetch_provider_neighbors", fail)
    before, events = durable_rows(library.database), []
    store = PaperStore(library.database)
    try:
        result = citation_intelligence.explore_citation_graph(store, library.paper_id,
            direction="references", depth=1, limit=5, refresh=True, profile_path=library.profile,
            progress=lambda *event: events.append(event))
    finally:
        store.close()
    assert len(result.errors) == 2
    assert_safe(result.errors)
    assert_safe(events)
    after = durable_rows(library.database)
    for table in before:
        if table != "citation_fetches":
            assert after[table] == before[table]
    assert len(after["citation_fetches"]) == 2
    assert_safe(after["citation_fetches"])


@pytest.mark.parametrize("status,attempts", [(403, 1), (404, 1), (429, 3), (500, 3), (503, 3)])
def test_http_retry_policy_preserves_status_and_bounds_waits(monkeypatch, status, attempts):
    calls, sleeps = [], []
    def fail(request, **kwargs):
        calls.append(request.full_url)
        raise urllib.error.HTTPError(URL, status, POISON, {"Retry-After": "999999999999"}, io.BytesIO())
    monkeypatch.setattr(http.urllib.request, "urlopen", fail)
    monkeypatch.setattr(http.time, "sleep", sleeps.append)
    with pytest.raises(urllib.error.HTTPError) as raised:
        http.fetch_bytes(URL, retries=2)
    assert raised.value.code == status
    assert len(calls) == attempts
    assert sleeps == [60.0] * (attempts - 1)


@pytest.mark.parametrize("kind,expected_status", [(403, "metadata_inaccessible"), (404, "metadata_inaccessible"),
    (429, "rate_limited"), (503, "provider_error"), ("timeout", "timeout"), ("offline", "network_unavailable")])
@pytest.mark.parametrize("endpoint", ["lookup", "search"])
def test_research_provider_errors_keep_status_and_saved_library(library, tmp_path, monkeypatch, kind, expected_status, endpoint):
    pytest.importorskip("fastapi", reason="optional local workspace dependency")
    pytest.importorskip("httpx", reason="optional TestClient dependency")
    from fastapi.testclient import TestClient
    import workspace_web
    import web.research_api as api

    monkeypatch.setattr(workspace_web, "ensure_user_defaults", lambda: None)
    def fail(*args, **kwargs):
        raise provider_error(kind)
    monkeypatch.setattr(api.venue_discovery, "lookup" if endpoint == "lookup" else "search_and_store", fail)
    before = durable_rows(library.database)
    app = workspace_web.create_app(library.database, semantic_enabled=False, research_results_root=tmp_path / "research")
    with TestClient(app) as client:
        path = "/api/research/venues/lookup" if endpoint == "lookup" else "/api/research/search"
        payload = {"query": "context fixture"} if endpoint == "lookup" else {
            "source_id": "S1", "query": "context fixture", "identifier": "failed-result"}
        response = client.post(path, json=payload)
        assert response.status_code == 502
        assert response.json()["detail"]["status"] == expected_status
        assert response.json()["detail"]["message"]
        assert_safe(response.text)
        assert client.get(f"/api/papers/{library.paper_id}").json()["notes"] == "Revised synthetic manual note Україна"
    assert durable_rows(library.database) == before
    assert not (tmp_path / "research" / "failed-result").exists()
