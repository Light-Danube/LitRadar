import argparse
import json
import urllib.error

import pytest

from config import RadarConfig
from sources.base import Paper
from sources.venues import Venue, VenueSearchResult
from storage.sqlite import PaperStore
import venue_discovery as discovery
from cli import build_parser


def venue(source_id="S1"):
    return Venue(source_id, "Collision Journal", "journal", "1234-5678", ("1234-5678",),
                 "Publisher", "https://api.openalex.org/sources/" + source_id,
                 "2026-10-14T00:00:00+00:00")


def result(source_id="S1", papers=None):
    papers = papers if papers is not None else [Paper(source="openalex", title="Context", doi="10.1/test",
                                                     external_id="https://openalex.org/W1", venue="Collision Journal")]
    return VenueSearchResult(venue(source_id), papers, 20, True, 1, 20,
                             {"retrieved_at": "2026-10-14T00:00:00+00:00", "query": "context", "source_id": source_id})


def test_cache_filters_and_refresh_preserve_personal_state(tmp_path, monkeypatch):
    store = PaperStore(tmp_path / "synthetic.sqlite")
    original = Paper(source="arxiv", title="Context", doi="10.1/test", external_id="1234.5678")
    pid = store.upsert_paper(original, relevance_score=.8, matched_groups={"context": ["context"]},
                             keyword_score=.6, semantic_score=.9, scoring_version="semantic-v0.2")
    store.set_notes(pid, "Особисті нотатки")
    store.set_tags(pid, ["manual"])
    store.set_status(pid, "read")
    calls = []
    def fake(query, source_id, **kwargs):
        calls.append((query, source_id, kwargs))
        return result(source_id)
    monkeypatch.setattr(discovery.venues, "search_venue", fake)
    first = discovery.search_and_store(store, "context", "S1", year_from=2023, year_to=2026)
    second = discovery.search_and_store(store, "context", "https://openalex.org/S1", year_from=2023, year_to=2026)
    assert first["paper_ids"] == [pid] and first["newly_stored"] == 0
    assert not first["cache_hit"] and second["cache_hit"] and len(calls) == 1
    for kwargs in ({"year_to": 2025}, {"limit": 5}, {"page": 2}, {"force": True}):
        discovery.search_and_store(store, "context", "S1", **kwargs)
    discovery.search_and_store(store, "sarcasm", "S2")
    assert len(calls) == 6
    row = store.get(pid)
    assert (row["notes"], json.loads(row["tags_json"]), row["status"]) == ("Особисті нотатки", ["manual"], "read")
    assert (row["semantic_score"], row["relevance_score"], row["scoring_version"]) == (.9, .8, "semantic-v0.2")
    assert set(store.identifiers_for_paper(pid)) >= {"doi", "arxiv_id", "openalex_id"}
    assert store.conn.execute("SELECT count(*) FROM discovery_venues").fetchone()[0] == 2
    observation = json.loads(store.conn.execute("SELECT observation_json FROM paper_venue_observations WHERE source_id='S1'").fetchone()[0])
    assert observation["venue"]["scopus_status"] == "unverified"
    store.close()


def test_conflicting_provider_alias_rejected_and_batch_rolled_back(tmp_path, monkeypatch):
    store = PaperStore(tmp_path / "synthetic.sqlite")
    store.upsert_paper(Paper(source="openalex", title="Same", doi="10.1/first", external_id="W1"),
                       relevance_score=0, matched_groups={})
    papers = [Paper(source="openalex", title="New", doi="10.1/new", external_id="W2"),
              Paper(source="openalex", title="Same", doi="10.1/conflict", external_id="W1")]
    monkeypatch.setattr(discovery.venues, "search_venue", lambda *a, **kw: result(papers=papers))
    with pytest.raises(ValueError, match="Conflicting DOI"):
        discovery.search_and_store(store, "context", "S1")
    assert store.total_count() == 1
    assert store.conn.execute("SELECT count(*) FROM discovery_venues").fetchone()[0] == 0
    assert store.conn.execute("SELECT count(*) FROM venue_search_cache").fetchone()[0] == 0
    store.close()


def test_existing_database_additive_migration(tmp_path):
    path = tmp_path / "synthetic.sqlite"
    store = PaperStore(path)
    pid = store.upsert_paper(Paper(source="fixture", title="Legacy"), relevance_score=0, matched_groups={})
    store.set_notes(pid, "Keep this")
    store.conn.executescript("DROP TABLE paper_venue_observations; DROP TABLE discovery_venues; DROP TABLE venue_search_cache;")
    store.close()
    reopened = PaperStore(path)
    assert reopened.get(pid)["notes"] == "Keep this"
    assert reopened.conn.execute("SELECT count(*) FROM discovery_venues").fetchone()[0] == 0
    reopened.close()


def test_zero_results_and_errors_do_not_cache_failures(tmp_path, monkeypatch):
    store = PaperStore(tmp_path / "synthetic.sqlite")
    monkeypatch.setattr(discovery.venues, "search_venue", lambda *a, **k: result(papers=[]))
    assert discovery.search_and_store(store, "context", "S1")["status"] == "zero_results"
    def fail(*args, **kwargs):
        raise TimeoutError()
    monkeypatch.setattr(discovery.venues, "search_venue", fail)
    with pytest.raises(TimeoutError):
        discovery.search_and_store(store, "different", "S1")
    assert store.conn.execute("SELECT count(*) FROM venue_search_cache").fetchone()[0] == 1
    store.close()


@pytest.mark.parametrize("exc,status", [
    (urllib.error.HTTPError("url", 429, "", {}, None), "rate_limited"),
    (urllib.error.HTTPError("url", 503, "", {}, None), "provider_error"),
    (urllib.error.HTTPError("url", 403, "", {}, None), "metadata_inaccessible"),
    (TimeoutError(), "timeout"), (urllib.error.URLError("blocked"), "network_unavailable"),
    (discovery.venues.VenueMetadataError("wrong identity"), "malformed_metadata"),
    (ValueError("bad source"), "invalid_request"),
])
def test_error_status(exc, status):
    assert discovery.error_status(exc) == status


def test_cli_workflow_with_fake_http_and_evidence_export(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(RadarConfig, "load", lambda: RadarConfig())
    monkeypatch.setattr(discovery.venues, "lookup_venues", lambda *a, **k: [venue(), venue("S2")])
    monkeypatch.setattr(discovery.venues, "search_venue", lambda *a, **k: result())
    parser = build_parser()
    db = str(tmp_path / "synthetic.sqlite")
    def run(*words):
        args = parser.parse_args(["--db", db, *words])
        assert args.func(args) == 0
        return capsys.readouterr().out
    assert json.loads(run("venue", "lookup", "Collision"))["status"] == "ambiguous_venue"
    assert json.loads(run("venue", "search", "S1", "context", "--year-from", "2023"))["paper_ids"] == [1]
    assert json.loads(run("evidence", "show", "1"))["revision"] == 0
    edit = tmp_path / "edit.json"
    edit.write_text(json.dumps({"user_questions": {"value": "Чи потрібен контекст?", "origin": "user"}}), encoding="utf-8")
    assert json.loads(run("evidence", "update", "1", str(edit), "--expected-revision", "0"))["revision"] == 1
    output = tmp_path / "matrix.md"
    run("evidence", "export", "1", "--output", str(output))
    assert "Чи потрібен контекст?" in output.read_text(encoding="utf-8")
    assert "not verified" in output.read_text(encoding="utf-8")


def test_cli_error_never_echoes_authenticated_url(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(RadarConfig, "load", lambda: RadarConfig())
    def fail(*a, **kw):
        raise urllib.error.URLError("https://api.openalex.org/?api_key=DO-NOT-PRINT")
    monkeypatch.setattr(discovery.venues, "lookup_venues", fail)
    args = build_parser().parse_args(["--db", str(tmp_path / "synthetic.sqlite"), "venue", "lookup", "context"])
    assert args.func(args) == 1
    output = capsys.readouterr().err
    assert "network_unavailable" in output and "DO-NOT-PRINT" not in output
