"""Uploaded labels/references remain data; fixtures never use a personal library."""
from __future__ import annotations

import base64
from contextlib import closing, contextmanager
import builtins
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import urllib.request

import pytest

from sources.base import Paper
from storage.evidence import EvidenceStore
from storage.sqlite import PaperStore


OUTSIDE_CONTENT = "SYNTHETIC_OUTSIDE_BYTES_MUST_NOT_BECOME_ANNOTATIONS"
REMOTE = "https://synthetic.invalid/never-fetch?api_key=synthetic-not-real"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    pytest.importorskip("fastapi", reason="optional local workspace dependency")
    pytest.importorskip("httpx", reason="optional TestClient dependency")
    from fastapi.testclient import TestClient
    import workspace_web

    database = tmp_path / "synthetic.sqlite3"
    store = PaperStore(database)
    try:
        paper_id = store.upsert_paper(Paper(source="fixture", title="Synthetic upload target"),
                                      relevance_score=0.5, matched_groups={})
        store.set_notes(paper_id, "Original synthetic manual note")
        store.set_notes(paper_id, "Revised manual note Україна")
        store.set_tags(paper_id, ["manual"])
        store.set_status(paper_id, "read")
        store.add_annotation(paper_id, "Existing manual annotation")
        removed = store.add_annotation(paper_id, "Deleted imported annotation", kind="imported")
        store.change_annotation_recovery(paper_id, removed["id"], expected_revision=1, delete=True)
        EvidenceStore(store).update(paper_id, {"method": {"value": "Reviewed method", "origin": "user"}})
    finally:
        store.close()
    outside = tmp_path / "outside-fixture.json"
    outside.write_text(json.dumps([{"content": OUTSIDE_CONTENT}]), encoding="utf-8")
    monkeypatch.setattr(workspace_web, "ensure_user_defaults", lambda: None)
    with TestClient(workspace_web.create_app(database, semantic_enabled=False,
                                            research_results_root=tmp_path / "research")) as client:
        yield client, database, paper_id, outside


def file_entry(filename, text, kind):
    return {"filename": filename, "format": kind,
            "content_base64": base64.b64encode(text.encode("utf-8")).decode("ascii")}


def durable_rows(database):
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
        result = {}
        for (name,) in connection.execute("SELECT name FROM sqlite_schema WHERE type='table'"):
            if name.startswith("papers_fts"):
                continue
            quoted = '"' + name.replace('"', '""') + '"'
            columns = len(connection.execute(f"PRAGMA table_info({quoted})").fetchall())
            order = ",".join(str(index) for index in range(1, columns + 1))
            result[name] = connection.execute(f"SELECT * FROM {quoted} ORDER BY {order}").fetchall()
        return result


@contextmanager
def deny_reference_access(monkeypatch, outside):
    """Guard JSON/RIS in the parent process, not optional parser subprocesses."""
    import llm.providers
    import sources.http

    target = os.path.normcase(os.path.abspath(outside))
    def guarded(original):
        def open_file(file, *args, **kwargs):
            if isinstance(file, (str, bytes, os.PathLike)):
                if os.path.normcase(os.path.abspath(os.fsdecode(file))) == target:
                    pytest.fail("Upload metadata was used to open the outside fixture")
            return original(file, *args, **kwargs)
        return open_file
    def denied(*args, **kwargs):
        pytest.fail("Local annotation import attempted network/provider/subprocess access")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", guarded(builtins.open))
        patch.setattr(io, "open", guarded(io.open))
        patch.setattr(os, "open", guarded(os.open))
        patch.setattr(urllib.request, "urlopen", denied)
        patch.setattr(socket, "getaddrinfo", denied)
        patch.setattr(socket, "create_connection", denied)
        patch.setattr(socket.socket, "connect", denied)
        patch.setattr(socket.socket, "connect_ex", denied)
        patch.setattr(sources.http, "fetch_bytes", denied)
        patch.setattr(llm.providers, "make_provider", denied)
        patch.setattr(subprocess, "run", denied)
        yield


def snapshot(path):
    return path.read_bytes(), path.stat().st_mtime_ns


def test_uploaded_json_and_ris_bytes_override_path_and_url_labels(workspace, monkeypatch):
    client, database, paper, outside = workspace
    source = f"{outside}; {outside.as_uri()}; {REMOTE}"
    ris = f"TY  - JOUR\nTI  - Uploaded RIS title\nL1  - {outside.as_uri()}\nUR  - {REMOTE}\nN1  - {outside}\nER  -\n"
    entries = [file_entry(str(outside), json.dumps([{"content": "Uploaded JSON Україна", "source_ref": source}]), "json"),
               file_entry(r"C:\synthetic\..\outside-fixture.ris", ris, "ris"),
               file_entry(REMOTE + "/label.json", '[{"content":"Uploaded URL label"}]', "json")]
    before = snapshot(outside)
    with deny_reference_access(monkeypatch, outside):
        response = client.post(f"/api/papers/{paper}/annotations/import-files", json={"files": entries})
    assert response.status_code == 200, response.text
    assert response.json()["added"] == 3
    items = response.json()["items"]
    imported_json = next(item for item in items if item["content"] == "Uploaded JSON Україна")
    assert imported_json["source_ref"] == f"{outside.name}: {source}"
    imported_ris = next(item for item in items if item["origin_method"] == "ris_import")
    fields = json.loads(imported_ris["content"])
    assert fields["TI"] == ["Uploaded RIS title"]
    assert fields["L1"] == [outside.as_uri()] and fields["UR"] == [REMOTE]
    assert fields["N1"] == [str(outside)]
    assert imported_ris["source_ref"] == "outside-fixture.ris: record 1"
    assert next(item for item in items if item["content"] == "Uploaded URL label")["source_ref"] == "label.json"
    assert OUTSIDE_CONTENT not in response.text
    assert snapshot(outside) == before
    assert client.get(f"/api/papers/{paper}").json()["notes"] == "Revised manual note Україна"


def test_failed_mixed_upload_preserves_all_manual_rows_and_outside_fixture(workspace, monkeypatch):
    client, database, paper, outside = workspace
    valid = file_entry(str(outside), json.dumps([{"content": "Must never commit", "source_ref": outside.as_uri()}]), "json")
    invalid = file_entry("../broken.ris", f"TY  - JOUR\nUR  - {REMOTE}\nL1  - {outside}\n", "ris")
    before, outside_before = durable_rows(database), snapshot(outside)
    with deny_reference_access(monkeypatch, outside):
        response = client.post(f"/api/papers/{paper}/annotations/import-files", json={"files": [valid, invalid]})
    assert response.status_code == 422
    assert "Must never commit" not in response.text and OUTSIDE_CONTENT not in response.text
    assert durable_rows(database) == before
    assert snapshot(outside) == outside_before


def test_legacy_json_import_also_treats_filename_and_source_reference_as_data(workspace, monkeypatch):
    client, _, paper, outside = workspace
    before = snapshot(outside)
    with deny_reference_access(monkeypatch, outside):
        response = client.post(f"/api/papers/{paper}/annotations/import", json={
            "filename": str(outside), "items": [{"content": "Explicit uploaded legacy entry", "source_ref": outside.as_uri()}]})
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    assert item["content"] == "Explicit uploaded legacy entry"
    assert item["source_ref"] == f"{outside}: {outside.as_uri()}"
    assert snapshot(outside) == before


def test_real_bibtex_worker_keeps_external_file_and_url_fields_as_metadata(workspace):
    """Real child parser/output evidence; parent read/network guards do not cover it."""
    pytest.importorskip("bibtexparser", reason="optional BibTeX adapter is not installed")
    client, _, paper, outside = workspace
    text = f"@article{{fixture, title={{Uploaded BibTeX title}}, file={{{outside.as_posix()}}}, url={{{REMOTE}}}}}"
    before = snapshot(outside)
    response = client.post(f"/api/papers/{paper}/annotations/import-files", json={
        "files": [file_entry(str(outside), text, "bibtex")]})
    assert response.status_code == 200, response.text
    item = response.json()["items"][0]
    record = json.loads(item["content"])
    assert record["title"] == "Uploaded BibTeX title"
    assert record["file"] == outside.as_posix() and record["url"] == REMOTE
    assert item["origin_method"] == "bibtex_import" and item["source_ref"] == f"{outside.name}: fixture"
    assert OUTSIDE_CONTENT not in response.text
    assert snapshot(outside) == before
