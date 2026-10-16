"""Public restore boundaries with disposable SQLite/files; no external services."""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3

import pytest

from storage.recovery import backup_library, restore_library


def snapshot(paths):
    return {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}


def symlink(path, target, *, directory=False):
    try:
        path.symlink_to(target, target_is_directory=directory)
    except OSError as exc:
        if os.name == "nt" and getattr(exc, "winerror", None) in {5, 1314}:
            pytest.skip("Windows runner lacks symlink creation privilege")
        raise


@pytest.fixture
def library_bundle(tmp_path):
    source = tmp_path / "source.sqlite3"
    # An older additive schema also demonstrates that backup/restore does not
    # initialize or migrate either the source or the restored database.
    with sqlite3.connect(source) as conn:
        conn.executescript("""
            CREATE TABLE papers (id INTEGER PRIMARY KEY, source TEXT, title TEXT,
                                 title_normalized TEXT, notes TEXT);
            INSERT INTO papers VALUES (7, 'synthetic', 'Synthetic title',
                                       'synthetic title', 'Synthetic note Україна');
        """)
    offline = tmp_path / "offline" / "7-synthetic"
    offline.mkdir(parents=True)
    note = offline / "notes.txt"
    note.write_text("Synthetic saved offline note", encoding="utf-8")
    sources = [source, note]
    before = snapshot(sources)
    bundle = backup_library(source, tmp_path / "bundle", offline=offline.parent,
                            writers_stopped=True)
    assert snapshot(sources) == before
    return source, bundle, sources, before


@pytest.mark.parametrize("link_kind", ["symlink", "hardlink"])
def test_restore_rejects_linked_manifest_without_touching_source_or_outside(tmp_path, library_bundle, link_kind):
    _, bundle, sources, before = library_bundle
    manifest = bundle / "manifest.json"
    outside = tmp_path / "outside-valid-manifest.json"
    outside.write_bytes(manifest.read_bytes())
    manifest.unlink()
    if link_kind == "symlink":
        symlink(manifest, outside)
    else:
        os.link(outside, manifest)
    outside_before = snapshot([outside])
    database_before = snapshot([bundle / "library.sqlite3"])
    destination = tmp_path / "restored"
    with pytest.raises(ValueError):
        restore_library(bundle, destination)
    assert not destination.exists()
    assert snapshot([outside]) == outside_before
    assert snapshot([bundle / "library.sqlite3"]) == database_before
    assert snapshot(sources) == before


def test_restore_rejects_artifact_directory_symlink_without_following_it(tmp_path, library_bundle):
    _, bundle, sources, before = library_bundle
    artifact_dir = bundle / "offline" / "7-synthetic"
    outside = tmp_path / "outside-artifacts"
    artifact_dir.rename(outside)
    symlink(artifact_dir, outside, directory=True)
    outside_files = list(outside.iterdir())
    outside_before = snapshot(outside_files)
    bundle_before = snapshot([bundle / "manifest.json", bundle / "library.sqlite3"])
    destination = tmp_path / "restored"
    with pytest.raises(ValueError):
        restore_library(bundle, destination)
    assert not destination.exists()
    assert list(outside.iterdir()) == outside_files
    assert snapshot(outside_files) == outside_before
    assert snapshot(bundle_before) == bundle_before
    assert snapshot(sources) == before


def test_restore_hardlinked_artifact_failure_removes_new_destination(tmp_path, library_bundle):
    _, bundle, sources, before = library_bundle
    artifact = bundle / "offline" / "7-synthetic" / "notes.txt"
    outside = tmp_path / "outside-notes.txt"
    outside.write_bytes(artifact.read_bytes())  # Exact bytes retain a valid checksum.
    artifact.unlink()
    os.link(outside, artifact)
    outside_before = snapshot([outside])
    bundle_files = [path for path in bundle.rglob("*") if path.is_file()]
    bundle_before = snapshot(bundle_files)
    destination = tmp_path / "restored"
    with pytest.raises(ValueError):
        restore_library(bundle, destination)
    assert not destination.exists()
    assert snapshot(bundle_files) == bundle_before
    assert snapshot([outside]) == outside_before
    assert snapshot(sources) == before


def test_restore_destination_parent_symlink_cannot_create_or_remove_outside_files(tmp_path, library_bundle):
    _, bundle, sources, before = library_bundle
    outside = tmp_path / "outside-destination"
    outside.mkdir()
    sentinel = outside / "retain.txt"
    sentinel.write_text("Synthetic destination sentinel", encoding="utf-8")
    outside_before = snapshot([sentinel])
    bundle_before = snapshot([path for path in bundle.rglob("*") if path.is_file()])
    linked_parent = tmp_path / "linked-destination"
    symlink(linked_parent, outside, directory=True)
    with pytest.raises(ValueError):
        restore_library(bundle, linked_parent / "restored")
    assert list(outside.iterdir()) == [sentinel]
    assert snapshot([sentinel]) == outside_before
    assert snapshot(bundle_before) == bundle_before
    assert snapshot(sources) == before


def test_read_only_source_and_bundle_restore_to_new_destination_without_migration(tmp_path, library_bundle):
    source, _, sources, before = library_bundle
    # Owner read-only mode is a disposable fixture, not a Windows ACL claim.
    readonly_paths = [source]
    try:
        source.chmod(0o400)
        bundle = backup_library(source, tmp_path / "readonly-source-backup")
        readonly_paths.extend(path for path in bundle.iterdir() if path.is_file())
        for path in readonly_paths:
            path.chmod(0o400)
        bundle_before = snapshot(readonly_paths)
        restored = restore_library(bundle, tmp_path / "new-destination")
        with sqlite3.connect(restored.as_uri() + "?mode=ro", uri=True) as conn:
            assert conn.execute("SELECT id, notes FROM papers").fetchall() == [(7, "Synthetic note Україна")]
            assert [row[1] for row in conn.execute("PRAGMA table_info(papers)")] == [
                "id", "source", "title", "title_normalized", "notes"]
            assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert snapshot(readonly_paths) == bundle_before
        assert snapshot(sources) == before
    finally:
        for path in readonly_paths:
            path.chmod(0o600)
