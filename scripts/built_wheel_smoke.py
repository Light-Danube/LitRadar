"""Run with the wheel interpreter outside the checkout; only synthetic local data."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from contextlib import closing
import sys
import tempfile


def _database_rows(path: Path) -> dict:
    """Compare durable rows and check integrity without leaving a Windows handle open."""
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
        tables = connection.execute("SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'papers_fts%'").fetchall()
        result = {}
        for (name,) in tables:
            quoted = '"' + name.replace('"', '""') + '"'
            columns = len(connection.execute(f"PRAGMA table_info({quoted})").fetchall())
            order = ",".join(str(index) for index in range(1, columns + 1))
            result[name] = connection.execute(f"SELECT * FROM {quoted} ORDER BY {order}").fetchall()
        return result


def _file_hashes(directory: Path) -> dict:
    return {path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in directory.rglob("*") if path.is_file()}


def _recovery_smoke(root: Path, database: Path, paper_id: int, run) -> None:
    """Exercise packaged recovery CLI, retaining real synthetic histories and elected files."""
    from sources.base import Paper
    from storage.evidence import EvidenceStore
    from storage.sqlite import PaperStore
    from storage.venue_presets import VenuePresetStore
    from web.research_files import ResearchFiles

    store = PaperStore(database)
    try:
        store.set_notes(paper_id, "Revised synthetic note Україна")
        neighbour = store.upsert_paper(Paper(source="fixture", external_id="wheel-neighbour",
                                             title="Synthetic wheel citation"),
                                      relevance_score=0.1, matched_groups={})
        store.record_relation(paper_id, neighbour, "cites", "fixture")
        store.record_feedback(paper_id, 1, reason="Synthetic wheel feedback")
        annotation = store.add_annotation(paper_id, "Synthetic original annotation")
        store.edit_annotation(paper_id, annotation["id"], expected_revision=1,
                              content="Synthetic revised annotation", review_status="accepted")
        store.change_annotation_recovery(paper_id, annotation["id"], expected_revision=2, delete=True)
        evidence = EvidenceStore(store)
        evidence.update(paper_id, {"method": {"value": "Synthetic method", "origin": "user"}})
        worksheet = evidence.update(paper_id, {"method": {"value": "Revised method", "origin": "user"}}, expected_revision=1)
        presets = VenuePresetStore(store)
        deleted = presets.list()[0]
        presets.delete(deleted["id"], deleted["revision"])
        active_presets = presets.list()
    finally:
        store.close()

    research = database.parent / "research"
    ResearchFiles(research).save("evidence", {"evidence.json": worksheet, "matrix.md": "# Synthetic evidence Україна\n"}, identifier="wheel-evidence")
    offline = database.parent / "offline"
    paper_directory = offline / f"{paper_id}-wheel"
    paper_directory.mkdir(parents=True)
    (paper_directory / "paper.pdf").write_bytes(b"%PDF-1.7\nSynthetic wheel fixture only")
    (paper_directory / "notes.txt").write_text("Synthetic saved note Україна", encoding="utf-8")
    expected_files = {f"{directory.name}/{path.relative_to(directory).as_posix()}": path.read_bytes()
                      for directory in (research, offline) for path in directory.rglob("*") if path.is_file()}
    before = _database_rows(database)
    bundle, destination = root / "library-backup", root / "library-restored"
    backup_arguments = ("--db", str(database), "library-backup", str(bundle),
                        "--research-dir", str(research), "--offline-dir", str(offline), "--writers-stopped")
    run(*backup_arguments)
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["included_artifacts"] == ["offline", "research"]
    assert manifest["artifact_writers_stopped"] is True
    assert {entry["path"] for entry in manifest["files"]} == {"library.sqlite3", *expected_files}
    for entry in manifest["files"]:
        data = (bundle / entry["path"]).read_bytes()
        assert entry["size"] == len(data) and entry["sha256"] == hashlib.sha256(data).hexdigest()
    run("library-restore", str(bundle), str(destination))
    restored = destination / "litradar.sqlite3"
    assert _database_rows(restored) == before, "Packaged recovery must preserve all durable rows and histories"
    assert _database_rows(database) == before, "Backup must not mutate source data"
    for relative, content in expected_files.items():
        assert (bundle / relative).read_bytes() == content
        assert (destination / relative).read_bytes() == content
    store = PaperStore(restored)
    try:
        paper = store.get(paper_id)
        assert paper["notes"] == "Revised synthetic note Україна"
        assert json.loads(paper["tags_json"]) == ["wheel"] and paper["status"] == "to-read"
        assert EvidenceStore(store).get(paper_id) == worksheet
        assert len(store.annotation_history(paper_id, annotation["id"])) == 3
        assert store.list_annotations(paper_id, deleted=True)[0]["id"] == annotation["id"]
        assert VenuePresetStore(store).list() == active_presets, "Deleted defaults must not be reseeded"
        assert store.feedback_count() == 1
    finally:
        store.close()
    run("--db", str(restored), "list")
    bundle_hashes, destination_hashes = _file_hashes(bundle), _file_hashes(destination)
    run(*backup_arguments, expected_code=1)
    run("library-restore", str(bundle), str(destination), expected_code=1)
    assert _file_hashes(bundle) == bundle_hashes and _file_hashes(destination) == destination_hashes
    assert _database_rows(restored) == before
    print("Installed-wheel recovery CLI round-trip, elected files/checksums, histories, integrity and no-overwrite passed")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="litbeacon-wheel-") as temporary:
        # Windows runner temporary paths may use a short name or junction alias.
        root = Path(temporary).resolve()
        os.environ["LITBEACON_HOME"] = str(root / "user")
        # Set the disposable home before any application imports.
        import cli
        import config
        import offline
        import telegram_bot
        from sources import cache
        from fastapi.testclient import TestClient
        from litradar_runtime import CODE_ROOT, WORKSPACE_ROOT, DEFAULT_DB, DEFAULT_PROFILE, DEFAULT_SCAN_CONFIG, VERSION
        from workspace_web import create_app, STATIC_ROOT

        assert not (CODE_ROOT / "pyproject.toml").exists(), "Smoke must import the installed wheel, not the checkout"
        assert Path(cli.__file__).parent == CODE_ROOT
        expected_home = (root / "user").resolve()
        assert WORKSPACE_ROOT == expected_home, f"Actual workspace {WORKSPACE_ROOT!s}; expected {expected_home!s}; temporary {temporary!s}"
        assert cli.build_parser().parse_args(["web", "--no-open-browser"]).host == "127.0.0.1"
        assert cli.DEFAULT_DB == DEFAULT_DB
        assert config.ENV_PATH == WORKSPACE_ROOT / ".env"
        assert offline.DEFAULT_OFFLINE_DIR.is_relative_to(WORKSPACE_ROOT)
        assert telegram_bot.DEFAULT_STATE.is_relative_to(WORKSPACE_ROOT)
        assert cache.DEFAULT_CACHE_DIR.is_relative_to(WORKSPACE_ROOT)

        def run(*arguments: str, expected_code: int = 0) -> str:
            result = subprocess.run([sys.executable, "-m", "cli", *arguments], cwd=root,
                                    check=False, capture_output=True, text=True)
            assert result.returncode == expected_code, result.stderr
            return result.stdout

        assert f"LitBeacon {VERSION}" in run("--version")
        assert "venue" in run("--help")
        run("init")
        assert DEFAULT_DB.is_file()
        assert json.loads(DEFAULT_PROFILE.read_text(encoding="utf-8"))["groups"]
        assert json.loads(DEFAULT_SCAN_CONFIG.read_text(encoding="utf-8"))["queries"]
        fixture = root / "fixture.json"
        fixture.write_text(json.dumps([{"source": "openalex", "external_id": "W123", "title": "Synthetic wheel paper", "abstract": "adaptive context", "authors": ["Test Researcher"]}]), encoding="utf-8")
        run("ingest-fixture", str(fixture), "--no-semantic")
        assert "Synthetic wheel paper" in run("list")
        with TestClient(create_app()) as client:
            assert client.get("/api/health").json()["ok"]
            assert "<html" in client.get("/").text.lower()
            assets = list(STATIC_ROOT.rglob("*"))
            assert any(path.suffix == ".png" for path in assets)
            for asset in assets:
                if asset.is_file():
                    response = client.get("/static/" + asset.relative_to(STATIC_ROOT).as_posix())
                    assert response.status_code == 200, asset
                    assert response.content == asset.read_bytes(), asset
            papers = client.get("/api/papers").json()["items"]
            paper_id = papers[0]["id"]
            assert client.patch(f"/api/papers/{paper_id}", json={"notes": "Synthetic note Україна", "tags": ["wheel"], "status": "to-read"}).status_code == 200
        # Reopening independently verifies durable storage, not just an API echo.
        with TestClient(create_app()) as client:
            paper = client.get(f"/api/papers/{paper_id}").json()
            assert paper["notes"] == "Synthetic note Україна"
            assert paper["tags"] == ["wheel"] and paper["status"] == "to-read"
        custom_db = root / "custom-library" / "custom.sqlite3"
        run("--db", str(custom_db), "init")
        with TestClient(create_app(custom_db)) as client:
            assert client.get("/api/health").json()["database"] == "custom.sqlite3"
            assert client.get("/api/papers").json()["items"] == []
            assert client.get("/static/app.js").status_code == 200
        DEFAULT_SCAN_CONFIG.write_text('{"queries": [], "scan": {"enabled": false}}', encoding="utf-8")
        run("init")
        assert json.loads(DEFAULT_SCAN_CONFIG.read_text(encoding="utf-8"))["queries"] == [], "Do not overwrite edited user defaults"
        _recovery_smoke(root, DEFAULT_DB, paper_id, run)
        assert not list(CODE_ROOT.glob("*.sqlite3"))
        print(f"Built wheel CLI/version/defaults/static assets/web/edit/restart smoke passed on {sys.platform}; version {VERSION}")


if __name__ == "__main__":
    main()
