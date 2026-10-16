"""Disposable filesystem fixtures for the immutable Research download boundary."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat

import pytest

from web.research_files import FileConflict, FileValidationError, ResearchFiles


PRIVATE = "SYNTHETIC_OUTSIDE_CONTENT_MUST_NOT_BE_SERVED"
IDENTIFIER = "synthetic-bundle"


@pytest.fixture
def bundle(tmp_path):
    files = ResearchFiles(tmp_path / "real-parent" / "research")
    artifact = files.save("venue_search", {"search.json": {"title": "Synthetic Україна"}},
                          identifier=IDENTIFIER, metadata={"status": "ok"})
    return files, artifact


def file_snapshot(path):
    return path.read_bytes(), path.stat().st_mtime_ns


def client_for(tmp_path, root):
    pytest.importorskip("fastapi", reason="optional browser workspace dependency")
    pytest.importorskip("httpx", reason="optional TestClient dependency")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from web.research_api import register_research_routes

    app = FastAPI()
    register_research_routes(app, tmp_path / "unused-synthetic.sqlite3", root)
    return TestClient(app)


def assert_generic_rejection(response, outside):
    assert response.status_code == 422
    assert response.json()["detail"]["status"] == "invalid_request"
    assert PRIVATE not in response.text
    assert str(outside) not in response.text
    assert str(outside.parent) not in response.text


def test_regular_bundle_lists_and_downloads_without_mutation(tmp_path, bundle):
    files, artifact = bundle
    data = files.path(IDENTIFIER, "search.json")
    manifest = files.path(IDENTIFIER, "manifest.json")
    before = {path.name: file_snapshot(path) for path in (data, manifest)}
    with client_for(tmp_path, files.root) as client:
        assert client.get("/api/research/artifacts").json() == {"items": [artifact]}
        response = client.get(f"/api/research/artifacts/{IDENTIFIER}/search.json")
        assert response.status_code == 200
        assert response.content == before["search.json"][0]
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "search.json" in response.headers["content-disposition"]
        manifest_response = client.get(f"/api/research/artifacts/{IDENTIFIER}/manifest.json")
        assert manifest_response.status_code == 200
        assert manifest_response.json() == artifact
    with pytest.raises(FileConflict):
        files.save("venue_search", {"search.json": {}}, identifier=IDENTIFIER)
    assert {path.name: file_snapshot(path) for path in (data, manifest)} == before
    assert not (tmp_path / "unused-synthetic.sqlite3").exists()


def test_hardlinked_artifact_cannot_serve_outside_content(tmp_path, bundle):
    files, _ = bundle
    outside = tmp_path / "outside-synthetic.json"
    outside.write_text(json.dumps({"private": PRIVATE}), encoding="utf-8")
    artifact = files.root / IDENTIFIER / "search.json"
    artifact.unlink()
    os.link(outside, artifact)
    before = file_snapshot(outside)
    with pytest.raises(FileValidationError):
        files.path(IDENTIFIER, "search.json")
    with client_for(tmp_path, files.root) as client:
        assert_generic_rejection(client.get(f"/api/research/artifacts/{IDENTIFIER}/search.json"), outside)
    assert file_snapshot(outside) == before
    assert not (tmp_path / "unused-synthetic.sqlite3").exists()


def test_hardlinked_manifest_is_not_listed_or_used_for_download(tmp_path, bundle):
    files, artifact = bundle
    outside = tmp_path / "outside-manifest.json"
    outside.write_text(json.dumps(artifact | {"metadata": {"private": PRIVATE}}), encoding="utf-8")
    manifest = files.root / IDENTIFIER / "manifest.json"
    manifest.unlink()
    os.link(outside, manifest)
    before = file_snapshot(outside)
    assert files.list() == []
    for name in ("manifest.json", "search.json"):
        with pytest.raises(FileValidationError):
            files.path(IDENTIFIER, name)
    with client_for(tmp_path, files.root) as client:
        assert client.get("/api/research/artifacts").json() == {"items": []}
        for name in ("manifest.json", "search.json"):
            assert_generic_rejection(client.get(f"/api/research/artifacts/{IDENTIFIER}/{name}"), outside)
    assert file_snapshot(outside) == before


@pytest.mark.parametrize("filename", ["search.json", "manifest.json"])
def test_nonregular_artifact_or_manifest_is_rejected_without_reading(tmp_path, bundle, filename):
    files, _ = bundle
    path = files.root / IDENTIFIER / filename
    path.unlink()
    path.mkdir()
    sentinel = path / "synthetic-sentinel.txt"
    sentinel.write_text(PRIVATE, encoding="utf-8")
    before = file_snapshot(sentinel)
    with pytest.raises(FileValidationError):
        files.path(IDENTIFIER, "search.json")
    if filename == "manifest.json":
        assert files.list() == []
    assert file_snapshot(sentinel) == before


@pytest.mark.parametrize("position", ["root", "parent", "bundle", "artifact", "manifest"])
def test_symlink_at_each_boundary_level_is_rejected(tmp_path, bundle, position):
    files, _ = bundle
    candidate = files
    outside = tmp_path / "outside-symlink-target"
    if position in {"root", "parent"}:
        target = files.root if position == "root" else files.root.parent
        outside.symlink_to(target, target_is_directory=True)
        candidate = ResearchFiles(outside if position == "root" else outside / "research")
        original = files.root / IDENTIFIER / "search.json"
    elif position == "bundle":
        original_bundle = files.root / IDENTIFIER
        original_bundle.rename(outside)
        original_bundle.symlink_to(outside, target_is_directory=True)
        original = outside / "search.json"
    else:
        name = "search.json" if position == "artifact" else "manifest.json"
        original = files.root / IDENTIFIER / name
        original.rename(outside)
        original.symlink_to(outside)
        original = outside
    before = file_snapshot(original)
    with pytest.raises(FileValidationError):
        candidate.path(IDENTIFIER, "search.json")
    if position in {"root", "parent"}:
        with pytest.raises(FileValidationError):
            candidate.list()
        with pytest.raises(FileValidationError):
            candidate.save("venue_search", {"search.json": {}}, identifier="new-bundle")
        assert not (files.root / "new-bundle").exists()
    elif position in {"bundle", "manifest"}:
        assert candidate.list() == []
    assert file_snapshot(original) == before


def test_simulated_windows_reparse_ancestor_blocks_read_list_and_write(tmp_path, bundle, monkeypatch):
    """Simulate the Windows stat flag; this is not a native junction test."""
    files, _ = bundle
    ancestor = files.root.parent
    original_lstat = Path.lstat
    class ReparseStat:
        st_file_attributes = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        def __init__(self, actual):
            self.actual = actual
        def __getattr__(self, name):
            return getattr(self.actual, name)

    def lstat(path, *args, **kwargs):
        actual = original_lstat(path, *args, **kwargs)
        return ReparseStat(actual) if path == ancestor else actual

    data = files.root / IDENTIFIER / "search.json"
    before = file_snapshot(data)
    monkeypatch.setattr(Path, "lstat", lstat)
    assert not ancestor.is_symlink(), "The flag must be caught independently of symlink mode"
    with pytest.raises(FileValidationError):
        files.path(IDENTIFIER, "search.json")
    with pytest.raises(FileValidationError):
        files.list()
    with pytest.raises(FileValidationError):
        files.save("venue_search", {"search.json": {}}, identifier="new-bundle")
    assert not (files.root / "new-bundle").exists()
    assert file_snapshot(data) == before
