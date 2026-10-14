"""CLI result bundles use the same local, portable result store as the browser."""
import json
from pathlib import Path

from cli import build_parser
from config import RadarConfig
from sources.base import Paper
from storage.sqlite import PaperStore
from sources.venues import Venue, VenueSearchResult
import venue_discovery


def test_cli_default_export_bundle_and_existing_explicit_output(tmp_path, capsys):
    db = tmp_path / "synthetic.sqlite"
    store = PaperStore(db)
    pid = store.upsert_paper(Paper(source="fixture", title="Synthetic context"), relevance_score=0, matched_groups={})
    store.set_notes(pid, "PERSONAL-NOTE-EXCLUDED")
    store.close()
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "evidence", "export", str(pid), "--identifier", "context-pilot"])
    assert args.func(args) == 0
    artifact = json.loads(capsys.readouterr().out)
    assert artifact["identifier"] == "context-pilot"
    bundle = tmp_path / "research" / "context-pilot"
    assert {"manifest.json", "matrix.md", "matrix.csv"} <= {p.name for p in bundle.iterdir()}
    assert "PERSONAL-NOTE-EXCLUDED" not in (bundle / "matrix.md").read_text()
    assert args.func(args) == 1  # Existing user-named bundle is never overwritten.
    capsys.readouterr()
    output = tmp_path / "explicit.md"
    args = parser.parse_args(["--db", str(db), "evidence", "export", str(pid), "--output", str(output)])
    assert args.func(args) == 0 and output.exists()


def test_cli_search_saved_and_invalid_name_precedes_provider(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(RadarConfig, "load", lambda: RadarConfig())
    venue = Venue("S1", "Synthetic journal", "journal", None, (), None,
                  "https://api.openalex.org/sources/S1", "2026-10-14T00:00:00+00:00")
    calls = []
    def search(*a, **kw):
        calls.append(a)
        return VenueSearchResult(venue, [Paper(source="openalex", title="Synthetic", external_id="W1")],
                                 1, False, 1, 20, {"source_id": "S1"})
    monkeypatch.setattr(venue_discovery.venues, "search_venue", search)
    db = tmp_path / "synthetic.sqlite"
    parser = build_parser()
    args = parser.parse_args(["--db", str(db), "venue", "search", "S1", "context", "--identifier", "pilot-search"])
    assert args.func(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["artifact"]["identifier"] == "pilot-search"
    assert (tmp_path / "research" / "pilot-search" / "search.json").exists()
    args = parser.parse_args(["--db", str(db), "venue", "search", "S1", "other", "--identifier", "../outside"])
    assert args.func(args) == 1 and len(calls) == 1


def test_cli_snapshot_failure_reports_committed_database(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(RadarConfig, "load", lambda: RadarConfig())
    venue = Venue("S1", "Synthetic journal", "journal", None, (), None,
                  "https://api.openalex.org/sources/S1", "2026-10-14T00:00:00+00:00")
    monkeypatch.setattr(venue_discovery.venues, "search_venue", lambda *a, **kw: VenueSearchResult(
        venue, [Paper(source="openalex", title="Synthetic saved", external_id="W1")],
        1, False, 1, 20, {"source_id": "S1"}))
    def fail(*a, **kw):
        raise OSError("private storage path")
    monkeypatch.setattr("web.research_files._Reservation.save", fail)
    db = tmp_path / "synthetic.sqlite"
    args = build_parser().parse_args(["--db", str(db), "venue", "search", "S1", "context"])
    assert args.func(args) == 1
    output = capsys.readouterr().err
    error = json.loads(output.splitlines()[-1])
    assert error["status"] == "save_failed" and error["saved_in_database"] is True
    assert "private storage path" not in output
    store = PaperStore(db)
    assert store.total_count() == 1
    store.close()
