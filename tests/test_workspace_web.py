from __future__ import annotations

import importlib.util
import json

import pytest

pytest.importorskip("fastapi", reason="browser workspace dependency is optional")
pytest.importorskip("httpx", reason="FastAPI TestClient requires httpx")

from fastapi.testclient import TestClient

from sources.base import Paper
from storage.sqlite import PaperStore
from workspace_web import create_app


def _insert(store: PaperStore, title: str, *, doi: str, venue: str = "", abstract: str = "context emotion attribution") -> int:
    return store.upsert_paper(
        Paper(source="fixture", title=title, abstract=abstract, published_at="2024-01-01", doi=doi, venue=venue),
        relevance_score=0.72,
        matched_groups={"context": 0.8},
    )


def test_workspace_serves_local_page_and_summary(tmp_path):
    db = tmp_path / "library.sqlite3"
    store = PaperStore(db)
    paper_id = _insert(store, "Context-aware emotion attribution", doi="10.1234/context", venue="NLP Review")
    store.set_tags(paper_id, ["context", "pragmatics"])
    store.close()

    client = TestClient(create_app(db))
    assert client.get("/").status_code == 200
    assert "LitBeacon" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    health = client.get("/api/health").json()
    assert health["ok"] is True
    assert health["legacy_name"] == "LitRadar"
    summary = client.get("/api/summary").json()
    assert summary["stats"]["all"] == 1
    assert summary["recent"][0]["id"] == paper_id


def test_workspace_filters_and_saves_annotations(tmp_path):
    db = tmp_path / "library.sqlite3"
    store = PaperStore(db)
    paper_id = _insert(store, "Sarcasm in dialogue", doi="10.1234/sarcasm", abstract="Sarcasm, context and pragmatic inference")
    store.close()
    client = TestClient(create_app(db))

    result = client.get("/api/papers", params={"q": "pragmatic inference", "status": "new"})
    assert result.status_code == 200
    assert result.json()["count"] == 1

    response = client.patch(f"/api/papers/{paper_id}", json={
        "status": "to-read", "tags": ["sarcasm", "pragmatics"], "notes": "Compare operational definitions."
    })
    assert response.status_code == 200
    item = response.json()
    assert item["status"] == "to-read"
    assert item["tags"] == ["pragmatics", "sarcasm"]
    assert item["notes"] == "Compare operational definitions."
    assert client.patch(f"/api/papers/{paper_id}", json={"status": "nonexistent"}).status_code == 422
    assert client.patch(f"/api/papers/{paper_id}", json={"unknown": "no"}).status_code == 422


def test_workspace_graph_is_bounded_and_direction_is_preserved(tmp_path):
    db = tmp_path / "library.sqlite3"
    store = PaperStore(db)
    seed = _insert(store, "Seed work on context", doi="10.1234/seed")
    prior = _insert(store, "Earlier work on pragmatic context", doi="10.1234/prior")
    later = _insert(store, "Later work on context attribution", doi="10.1234/later")
    store.conn.execute(
        "INSERT INTO paper_relations(source_paper_id,target_paper_id,relation_type,provider,observed_at) VALUES(?,?,?,?,?)",
        (seed, prior, "cites", "fixture", "2026-10-01T00:00:00+00:00"),
    )
    store.conn.execute(
        "INSERT INTO paper_relations(source_paper_id,target_paper_id,relation_type,provider,observed_at) VALUES(?,?,?,?,?)",
        (later, seed, "cites", "fixture", "2026-10-01T00:00:00+00:00"),
    )
    store.conn.commit()
    store.close()

    client = TestClient(create_app(db))
    graph = client.get("/api/graph", params={"seed_id": seed, "depth": 1, "max_nodes": 2}).json()
    assert len(graph["nodes"]) <= 2
    assert all(edge["source"] and edge["target"] for edge in graph["edges"])
    assert all(edge["type"] == "cites" for edge in graph["edges"])
    assert client.get("/api/graph", params={"seed_id": 999}).status_code == 404


def test_workspace_clusters_are_clearly_labelled_heuristics(tmp_path):
    db = tmp_path / "library.sqlite3"
    store = PaperStore(db)
    first = _insert(store, "Context-aware emotion classification", doi="10.1234/one", abstract="Context-aware emotion classification and pragmatic inference")
    second = _insert(store, "Pragmatic context in emotion analysis", doi="10.1234/two", abstract="Pragmatic context shapes emotion analysis and inference")
    store.set_tags(first, ["emotion"])
    store.set_tags(second, ["emotion"])
    store.close()

    result = TestClient(create_app(db)).get("/api/clusters").json()
    assert result["method"] == "heuristic"
    assert "not embedding-based" in result["description"]
    assert any(cluster["label"] == "Tag · emotion" and cluster["size"] == 2 for cluster in result["clusters"])


def test_workspace_job_controls_call_existing_scheduler_commands(monkeypatch, tmp_path):
    import subprocess

    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    client = TestClient(create_app(tmp_path / "library.sqlite3"))

    removed = client.post("/api/jobs/digest/remove")
    assert removed.status_code == 200
    assert removed.json()["job"] == "digest"
    assert "schedule" in calls[0][0]
    assert "remove" in calls[0][0]
    assert "digest" in calls[0][0]

    installed = client.post("/api/jobs/install-defaults")
    assert installed.status_code == 200
    assert len(calls) == 3
    assert "--job" in calls[1][0] and "scan" in calls[1][0]
    assert "--job" in calls[2][0] and "digest" in calls[2][0]
