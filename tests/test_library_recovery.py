"""Only synthetic disposable libraries/artifacts; no services or personal files."""
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from sources.base import Paper
from storage import recovery
from storage.evidence import EvidenceStore
from storage.sqlite import PaperStore
from storage.venue_presets import VenuePresetStore


def populated(path):
    store = PaperStore(path)
    one = store.upsert_paper(Paper(source="fixture", external_id="a", title="Synthetic Україна",
                                  doi="10.1000/synthetic", authors=["A. Fixture"],
                                  abstract="Synthetic only", venue="Fixture venue"),
                             relevance_score=.7, matched_groups={"fixture": ["synthetic"]})
    two = store.upsert_paper(Paper(source="fixture", external_id="b", title="Second fixture"),
                             relevance_score=.3, matched_groups={})
    store.set_notes(one, "First synthetic note")
    store.set_notes(one, "Edited synthetic note")
    store.set_tags(one, ["manual", "українська"])
    store.set_status(one, "read")
    store.set_status(two, "dismissed", dismiss_reason="Synthetic reason")
    store.set_llm_assessment(one, {"summary": "Synthetic saved assessment, no model used"})
    store.record_feedback(one, 1, reason="Synthetic useful")
    store.record_relation(one, two, "cites", "fixture")
    annotation = store.add_annotation(one, "Original synthetic evidence", kind="imported",
                                      source_ref="fixture", origin_method="json_import")
    store.edit_annotation(one, annotation["id"], expected_revision=1,
                          content="Edited evidence", review_status="accepted")
    store.change_annotation_recovery(one, annotation["id"], expected_revision=2, delete=True)
    evidence = EvidenceStore(store)
    evidence.update(one, {"method": {"value": "Synthetic method", "origin": "user"}})
    evidence.update(one, {"method": {"value": "Revised method", "origin": "user"}}, expected_revision=1)
    presets = VenuePresetStore(store)
    deleted = presets.list()[0]
    presets.delete(deleted["id"], deleted["revision"])
    store.record_research_run(job="synthetic", started_at="2026-01-01", completed_at="2026-01-01",
                              status="ok", summary={})
    store.close()
    return one, two


def rows(path):
    with sqlite3.connect(path) as conn:
        return {name: table_rows(conn, name)
                for (name,) in conn.execute("SELECT name FROM sqlite_schema WHERE type='table'")
                if name != "papers_fts"}


def table_rows(conn, name):
    columns = len(conn.execute(f'PRAGMA table_info("{name}")').fetchall())
    order = ",".join(str(i) for i in range(1, columns + 1))
    return [tuple(row) for row in conn.execute(f'SELECT * FROM "{name}" ORDER BY {order}')]


@pytest.fixture
def library(tmp_path):
    path = tmp_path / "synthetic.sqlite3"
    populated(path)
    return path


def manifest(bundle):
    return json.loads((bundle / "manifest.json").read_text())


def write_manifest(bundle, data):
    (bundle / "manifest.json").write_text(json.dumps(data), encoding="utf-8")


def rechecksum(bundle):
    data = manifest(bundle)
    for item in data["files"]:
        content = (bundle / item["path"]).read_bytes()
        item.update(size=len(content), sha256=hashlib.sha256(content).hexdigest())
    write_manifest(bundle, data)


def symlink(path, target, **kwargs):
    try:
        path.symlink_to(target, **kwargs)
    except OSError as exc:
        if os.name == "nt" and getattr(exc, "winerror", None) in {5, 1314}:
            pytest.skip("Windows runner lacks symlink creation privilege (Developer Mode/admin required)")
        raise


def test_wal_snapshot_preserves_committed_state_without_source_migration(library, tmp_path, monkeypatch):
    writer = sqlite3.connect(library)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("UPDATE papers SET notes='Committed active WAL note' WHERE id=1")
        writer.commit()
        assert Path(str(library) + "-wal").stat().st_size > 0
        expected = rows(library)
        source_schema = writer.execute("SELECT * FROM sqlite_schema ORDER BY name").fetchall()
        def forbidden(*args, **kwargs):
            raise AssertionError("Backup must not initialize/migrate the source")
        monkeypatch.setattr(PaperStore, "__init__", forbidden)
        bundle = recovery.backup_library(library, tmp_path / "backup")
        restored = recovery.restore_library(bundle, tmp_path / "restored")
        assert rows(restored) == expected
        assert rows(library) == expected
        assert writer.execute("SELECT * FROM sqlite_schema ORDER BY name").fetchall() == source_schema
        assert not (bundle / "library.sqlite3-wal").exists()
        assert not (restored.parent / "library.sqlite3-wal").exists()
    finally:
        writer.close()


def test_full_state_artifact_roundtrip_and_tombstones(library, tmp_path):
    research = tmp_path / "research" / "synthetic-result"
    research.mkdir(parents=True)
    (research / "manifest.json").write_text('{"synthetic":true}')
    (research / "evidence.json").write_text('{"method":"Synthetic only"}')
    (research / "matrix.md").write_text("# Synthetic evidence\n")
    offline = tmp_path / "offline" / "1-synthetic"
    offline.mkdir(parents=True)
    (offline / "paper.pdf").write_bytes(b"%PDF-1.7\nSynthetic fixture only")
    (offline / "notes.txt").write_text("Synthetic saved note")
    (tmp_path / ".env").write_text("SYNTHETIC_SECRET=not-a-real-credential")
    expected = rows(library)
    bundle = recovery.backup_library(library, tmp_path / "backup", research=research.parent,
                                     offline=offline.parent, writers_stopped=True)
    data = manifest(bundle)
    assert data["artifact_writers_stopped"] is True
    assert data["included_artifacts"] == ["offline", "research"]
    assert any("credentials" in item for item in data["excluded"])
    assert not (bundle / ".env").exists()
    restored = recovery.restore_library(bundle, tmp_path / "restored")
    assert rows(restored) == expected  # Every user field, ID, history, relation and tombstone.
    for group in (research.parent, offline.parent):
        for source in group.rglob("*"):
            if source.is_file():
                assert (restored.parent / group.name / source.relative_to(group)).read_bytes() == source.read_bytes()
    opened = PaperStore(restored)
    assert len(VenuePresetStore(opened).list()) == 2  # Deleted default is not reseeded.
    assert opened.conn.execute("SELECT COUNT(*) FROM paper_annotations WHERE deleted_at IS NOT NULL").fetchone()[0] == 1
    assert opened.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not opened.conn.execute("PRAGMA foreign_key_check").fetchall()
    opened.close()


def test_artifacts_require_stopped_writers_and_election(library, tmp_path):
    root = tmp_path / "research"
    root.mkdir()
    with pytest.raises(ValueError, match="writers-stopped"):
        recovery.backup_library(library, tmp_path / "backup", research=root)
    assert not (tmp_path / "backup").exists()
    bundle = recovery.backup_library(library, tmp_path / "backup")
    assert manifest(bundle)["included_artifacts"] == []


@pytest.mark.parametrize("path", ["../outside", "/absolute", "C:/evil", "research/x/../evil",
                                    "research\\x\\evil", "research/x/.env", "research/x/NUL.json",
                                    "research/x/manifest.json.", "research/x/file:stream", "research//matrix.md",
                                    "offline/x/token.json", "offline/x/runtime.log", "research/x/cache.json",
                                    "research/x/../../outside", "research/x\u0000/matrix.md"])
def test_malicious_or_excluded_manifest_paths_rejected(library, tmp_path, path):
    bundle = recovery.backup_library(library, tmp_path / "backup")
    data = manifest(bundle)
    data["files"].append({"path": path, "size": 0, "sha256": "0" * 64})
    write_manifest(bundle, data)
    with pytest.raises(ValueError):
        recovery.restore_library(bundle, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


@pytest.mark.parametrize("damage", ["duplicate", "missing", "corrupt", "invalid-size", "invalid-sha", "unknown-version", "extra", "database-corrupt"])
def test_damaged_bundles_rejected_and_destination_cleaned(library, tmp_path, damage):
    bundle = recovery.backup_library(library, tmp_path / "backup")
    data = manifest(bundle)
    item = data["files"][0]
    if damage == "duplicate":
        data["files"].append(dict(item))
    elif damage == "missing":
        (bundle / item["path"]).unlink()
    elif damage == "corrupt":
        with (bundle / item["path"]).open("ab") as handle:
            handle.write(b"corrupt")
    elif damage == "invalid-size":
        item["size"] = True
    elif damage == "invalid-sha":
        item["sha256"] = "no"
    elif damage == "unknown-version":
        data["version"] = 100
    elif damage == "extra":
        (bundle / "unlisted.txt").write_text("unexpected")
    elif damage == "database-corrupt":
        (bundle / item["path"]).write_bytes(b"Not SQLite")
        item["size"] = 10
        item["sha256"] = hashlib.sha256(b"Not SQLite").hexdigest()
    write_manifest(bundle, data)
    with pytest.raises((ValueError, sqlite3.Error)):
        recovery.restore_library(bundle, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_duplicate_json_keys_and_case_colliding_paths(library, tmp_path):
    bundle = recovery.backup_library(library, tmp_path / "backup")
    raw = (bundle / "manifest.json").read_text()
    (bundle / "manifest.json").write_text(raw.replace('"version": 1', '"version": 1, "version": 1'))
    with pytest.raises(ValueError, match="manifest"):
        recovery.restore_library(bundle, tmp_path / "restored")
    (bundle / "manifest.json").write_text(raw)
    data = manifest(bundle)
    data["files"].extend([{"path": f"offline/{folder}/paper.pdf", "size": 0, "sha256": "0" * 64}
                          for folder in ["fixture", "FIXTURE"]])
    with pytest.raises(ValueError, match="case-colliding"):
        write_manifest(bundle, data)
        recovery.restore_library(bundle, tmp_path / "restored")


def test_backup_rejects_case_colliding_artifact_directories(library, tmp_path):
    root = tmp_path / "offline"
    (root / "Foo").mkdir(parents=True)
    (root / "foo").mkdir(exist_ok=True)
    if (root / "Foo").samefile(root / "foo"):
        pytest.skip("Filesystem is case-insensitive; cannot create case-colliding directories")
    (root / "Foo" / "notes.txt").write_text("Synthetic note")
    (root / "foo" / "paper.pdf").write_bytes(b"%PDF-1.7\nSynthetic")
    with pytest.raises(ValueError, match="Case-colliding"):
        recovery.backup_library(library, tmp_path / "backup", offline=root, writers_stopped=True)
    assert not (tmp_path / "backup").exists()


def test_no_overwrite_including_empty_directory(library, tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(ValueError, match="already exists"):
        recovery.backup_library(library, existing)
    bundle = recovery.backup_library(library, tmp_path / "backup")
    (existing / "sentinel").write_text("retain")
    with pytest.raises(ValueError, match="already exists"):
        recovery.restore_library(bundle, existing)
    assert (existing / "sentinel").read_text() == "retain"


def test_symlink_and_hardlink_source_bundle_and_destination_rejected(library, tmp_path):
    link = tmp_path / "linked-library"
    symlink(link, library)
    with pytest.raises(ValueError, match="Symlink"):
        recovery.backup_library(link, tmp_path / "backup")
    bundle = recovery.backup_library(library, tmp_path / "backup")
    db = bundle / "library.sqlite3"
    db.unlink()
    symlink(db, library)
    with pytest.raises(ValueError, match="[Ss]ymlink"):
        recovery.restore_library(bundle, tmp_path / "restored")
    db.unlink()
    db.hardlink_to(library)
    with pytest.raises(ValueError, match="non-linked"):
        recovery.restore_library(bundle, tmp_path / "restored")
    real = tmp_path / "real"
    real.mkdir()
    parent = tmp_path / "link-parent"
    symlink(parent, real, target_is_directory=True)
    with pytest.raises(ValueError, match="Symlink"):
        recovery.backup_library(library, parent / "backup")


@pytest.mark.parametrize("failure", ["backup", "restore"])
def test_injected_copy_failure_removes_reserved_destination(library, tmp_path, monkeypatch, failure):
    bundle = recovery.backup_library(library, tmp_path / "backup") if failure == "restore" else None
    def fail(*args, **kwargs):
        raise OSError("Injected synthetic disk failure")
    monkeypatch.setattr(recovery, "_copy", fail)
    destination = tmp_path / "failed"
    with pytest.raises(OSError, match="Injected"):
        if failure == "backup":
            recovery.backup_library(library, destination)
        else:
            recovery.restore_library(bundle, destination)
    assert not destination.exists()
    assert library.exists()


def test_foreign_key_violation_rejected_even_with_valid_checksums(library, tmp_path):
    bundle = recovery.backup_library(library, tmp_path / "backup")
    with sqlite3.connect(bundle / "library.sqlite3") as conn:
        conn.execute("INSERT INTO feedback_events(paper_id,signal,reason,created_at) VALUES(9999,1,'fixture','fixture')")
    rechecksum(bundle)
    with pytest.raises(ValueError, match="foreign key"):
        recovery.restore_library(bundle, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


@pytest.mark.parametrize("sql", [
    "CREATE TRIGGER malicious AFTER INSERT ON papers BEGIN DELETE FROM papers; END",
    "CREATE VIEW malicious AS SELECT load_extension('untrusted')",
    "CREATE VIRTUAL TABLE malicious USING fts5(secret)",
    "DROP TRIGGER papers_fts_ai; CREATE TRIGGER papers_fts_ai AFTER INSERT ON papers BEGIN DELETE FROM papers; END",
])
def test_unsupported_executable_schema_rejected_before_app_open(library, tmp_path, sql):
    bundle = recovery.backup_library(library, tmp_path / "backup")
    with sqlite3.connect(bundle / "library.sqlite3") as conn:
        conn.executescript(sql)
    rechecksum(bundle)
    with pytest.raises(ValueError, match="Unsupported"):
        recovery.restore_library(bundle, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_symlinked_sqlite_sidecar_rejected(library, tmp_path):
    symlink(Path(str(library) + "-wal"), library)
    with pytest.raises(ValueError, match="Symlink"):
        recovery.backup_library(library, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


def test_windows_reparse_attribute_rejected_on_parent_component(tmp_path, monkeypatch):
    root = tmp_path / "synthetic-parent"
    root.mkdir()
    original = Path.lstat
    def fake_stat(path, *args, **kwargs):
        real = original(path, *args, **kwargs)
        if path == root:
            return SimpleNamespace(st_mode=real.st_mode, st_file_attributes=0x400)
        return real
    monkeypatch.setattr(Path, "lstat", fake_stat)
    with pytest.raises(ValueError, match="reparse-point"):
        recovery._safe_path(root / "new-destination")


def test_windows_reparse_attribute_rejected_during_directory_inventory(tmp_path, monkeypatch):
    root = tmp_path / "synthetic-artifacts"
    root.mkdir()
    class FakeEntry:
        path = str(root / "junction")
        def stat(self, *, follow_symlinks):
            assert follow_symlinks is False
            return SimpleNamespace(st_mode=0o40700, st_file_attributes=0x400)
    class FakeScan:
        def __enter__(self):
            return iter([FakeEntry()])
        def __exit__(self, *args):
            pass
    monkeypatch.setattr(recovery.os, "scandir", lambda path: FakeScan())
    with pytest.raises(ValueError, match="reparse-point"):
        recovery._files(root)


def test_unlisted_credentials_and_artifact_copy_failure_never_publish(library, tmp_path, monkeypatch):
    root = tmp_path / "research"
    folder = root / "fixture"
    folder.mkdir(parents=True)
    (folder / ".env").write_text("SYNTHETIC=not-real")
    with pytest.raises(ValueError, match="Hidden"):
        recovery.backup_library(library, tmp_path / "backup", research=root, writers_stopped=True)
    assert not (tmp_path / "backup").exists()
    (folder / ".env").unlink()
    (folder / "matrix.md").write_text("Synthetic")
    original = recovery._copy
    def fail_artifact(source, dest, **kwargs):
        if source.name == "matrix.md":
            raise OSError("Injected artifact failure")
        return original(source, dest, **kwargs)
    monkeypatch.setattr(recovery, "_copy", fail_artifact)
    with pytest.raises(OSError, match="artifact"):
        recovery.backup_library(library, tmp_path / "backup", research=root, writers_stopped=True)
    assert not (tmp_path / "backup").exists()


def test_artifact_changed_during_read_rejected(library, tmp_path, monkeypatch):
    root = tmp_path / "offline"
    folder = root / "1-fixture"
    folder.mkdir(parents=True)
    artifact = folder / "notes.txt"
    artifact.write_text("Synthetic original")
    original_reader = recovery._reader
    class MutatingReader:
        def __init__(self, path):
            self.handle = original_reader(path)
            self.changed = False
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.handle.close()
        def fileno(self):
            return self.handle.fileno()
        def read(self, size):
            data = self.handle.read(size)
            if not self.changed:
                self.changed = True
                artifact.write_text("Synthetic modified while copying")
            return data
    monkeypatch.setattr(recovery, "_reader", lambda p: MutatingReader(p) if p == artifact else original_reader(p))
    with pytest.raises(ValueError, match="changed"):
        recovery.backup_library(library, tmp_path / "backup", offline=root, writers_stopped=True)
    assert not (tmp_path / "backup").exists()


@pytest.mark.parametrize("setting,value", [("MAX_TOTAL_BYTES", 10), ("MAX_FILES", 0), ("MAX_SECONDS", -1)])
def test_total_count_and_time_bounds(library, tmp_path, monkeypatch, setting, value):
    bundle = recovery.backup_library(library, tmp_path / "backup")
    monkeypatch.setattr(recovery, setting, value)
    with pytest.raises((ValueError, sqlite3.Error)):
        recovery.restore_library(bundle, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_artifact_manifest_types_are_rejected(library, tmp_path):
    bundle = recovery.backup_library(library, tmp_path / "backup")
    data = manifest(bundle)
    data["included_artifacts"] = [{}]
    write_manifest(bundle, data)
    with pytest.raises(ValueError, match="artifact groups"):
        recovery.restore_library(bundle, tmp_path / "restored")


def test_file_and_manifest_bounds(library, tmp_path, monkeypatch):
    monkeypatch.setattr(recovery, "MAX_FILE_BYTES", 10)
    with pytest.raises(ValueError, match="oversized"):
        recovery.backup_library(library, tmp_path / "backup")
    assert not (tmp_path / "backup").exists()
    monkeypatch.setattr(recovery, "MAX_FILE_BYTES", 1024 ** 3)
    bundle = recovery.backup_library(library, tmp_path / "backup")
    monkeypatch.setattr(recovery, "MAX_MANIFEST_BYTES", 5)
    with pytest.raises(ValueError, match="Manifest"):
        recovery.restore_library(bundle, tmp_path / "restored")


def test_restored_synthetic_legacy_upgrade_twice_preserves_manual_fields_ids_and_history(library, tmp_path):
    with sqlite3.connect(library) as conn:
        for trigger in ["papers_fts_ai", "papers_fts_ad", "papers_fts_au"]:
            conn.execute(f"DROP TRIGGER IF EXISTS {trigger}")
        conn.execute("DROP TABLE papers_fts")
        conn.execute("DROP INDEX IF EXISTS idx_papers_references")
        conn.execute("DROP INDEX IF EXISTS idx_papers_influential_citations")
        for column in ["reference_count", "influential_citation_count", "source_tags_json"]:
            conn.execute(f"ALTER TABLE papers DROP COLUMN {column}")
    before = rows(library)
    with sqlite3.connect(library) as conn:
        old_columns = [row[1] for row in conn.execute("PRAGMA table_info(papers)")]
        schema = conn.execute("SELECT * FROM sqlite_schema ORDER BY name").fetchall()
    bundle = recovery.backup_library(library, tmp_path / "backup")
    restored = recovery.restore_library(bundle, tmp_path / "restored")
    assert rows(restored) == before
    with sqlite3.connect(library) as conn:
        assert conn.execute("SELECT * FROM sqlite_schema ORDER BY name").fetchall() == schema
    after_first = None
    for _ in range(2):
        opened = PaperStore(restored)
        assert not opened.conn.execute("PRAGMA foreign_key_check").fetchall()
        assert opened.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        selected = ",".join(f'"{column}"' for column in old_columns)
        assert [tuple(row) for row in opened.conn.execute(f"SELECT {selected} FROM papers ORDER BY id")] == before["papers"]
        for name, expected in before.items():
            if name not in {"papers", "sqlite_sequence"}:
                assert table_rows(opened.conn, name) == expected
        assert len(VenuePresetStore(opened).list()) == 2
        opened.close()
        current = rows(restored)
        if after_first is not None:
            assert current == after_first
        after_first = current


def test_cli_operations_are_distinct_from_paper_status_restore(library, tmp_path, capsys):
    from cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["--db", str(library), "library-backup", str(tmp_path / "backup")])
    assert args.func(args) == 0
    args = parser.parse_args(["library-restore", str(tmp_path / "backup"), str(tmp_path / "restored")])
    assert args.func(args) == 0
    assert (tmp_path / "restored" / "litradar.sqlite3").exists()
    assert "restored into new destination" in capsys.readouterr().out
    args = parser.parse_args(["library-restore", str(tmp_path / "backup"), str(tmp_path / "restored")])
    assert args.func(args) == 1
    assert "already exists" in capsys.readouterr().err
    assert parser.parse_args(["restore", "1"]).func.__name__ == "cmd_restore"
