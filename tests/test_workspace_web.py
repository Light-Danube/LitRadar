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


def test_annotation_api_separates_origins_and_supports_stable_pagination(tmp_path):
    db = tmp_path / "library.sqlite3"
    store = PaperStore(db)
    paper_id = _insert(store, "Annotation test", doi="10.1234/annotations")
    store.close()
    client = TestClient(create_app(db))
    url = f"/api/papers/{paper_id}/annotations"
    assert client.get(url).json()["note_provenance"] is None
    assert client.get(url).json()["items"] == []
    client.patch(f"/api/papers/{paper_id}", json={"notes": "Personal note"})
    ids = []
    for kind in ("user", "imported", "extracted", "generated"):
        response = client.post(url, json={"kind": kind, "content": "Текст <script>literal</script>",
                                          "source_ref": "file.pdf / page 3"})
        assert response.status_code == 201
        item = response.json()
        assert item["kind"] == kind and item["recorded_at"]
        assert item["channel"] == "annotation"
        ids.append(item["id"])
    page = client.get(url, params={"limit": 2}).json()
    assert [item["id"] for item in page["items"]] == list(reversed(ids[-2:]))
    assert page["has_more"] is True
    assert page["note_provenance"]["content"] == "Personal note"
    assert page["note_provenance"]["kind"] == "user"
    client.post(url, json={"content": "New entry between page requests"})
    older = client.get(url, params={"limit": 2, "before_id": page["next_before_id"]}).json()
    assert [item["id"] for item in older["items"]] == list(reversed(ids[:2]))
    assert older["has_more"] is False and older["next_before_id"] is None
    assert client.get(f"/api/papers/{paper_id}").json()["notes"] == "Personal note"


def test_annotation_api_rejects_invalid_input_and_missing_papers(tmp_path):
    db = tmp_path / "library.sqlite3"
    store = PaperStore(db)
    paper_id = _insert(store, "Annotation validation", doi="10.1234/validation")
    store.close()
    client = TestClient(create_app(db))
    url = f"/api/papers/{paper_id}/annotations"
    for payload in ({"content": ""}, {"content": " "}, {"content": "x", "kind": "legacy"},
                    {"content": "x", "unexpected": True}, {"content": "x" * 50_001},
                    {"content": "x", "source_ref": "x" * 2001}):
        assert client.post(url, json=payload).status_code == 422
    assert client.get(url + "?limit=201").status_code == 422
    assert client.get(url + "?before_id=0").status_code == 422
    assert client.get("/api/papers/999/annotations").status_code == 404
    assert client.post("/api/papers/999/annotations", json={"content": "x"}).status_code == 404


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


@pytest.fixture
def mixed_graph(tmp_path):
    db = tmp_path / "mixed.sqlite3"
    with_store = PaperStore(db)
    ids = [_insert(with_store, title, doi=f"10.1234/{index}") for index, title in enumerate(
        ["Seed", "Reference", "Citing paper", "Related paper", "Second hop"]
    )]
    seed, prior, later, related, distant = ids
    for source, target, kind, provider in [
        (seed, prior, "cites", "openalex"),
        (seed, prior, "cites", "semantic_scholar"),
        (later, seed, "cites", "semantic_scholar"),
        (seed, related, "related", "openalex"),
        (prior, distant, "cites", "openalex"),
    ]:
        with_store.conn.execute(
            "INSERT INTO paper_relations VALUES(?,?,?,?,?)",
            (source, target, kind, provider, "2026-10-12T12:00:00+00:00"),
        )
    with_store.conn.commit()
    with_store.close()
    return TestClient(create_app(db)), ids


def test_graph_deduplicates_providers_preserving_direction_and_provenance(mixed_graph):
    client, (seed, prior, later, related, _) = mixed_graph
    graph = client.get("/api/graph", params={"seed_id": seed}).json()
    assert len(graph["edges"]) == 3
    edge = next(e for e in graph["edges"] if e["target"] == str(prior))
    assert edge["source"] == str(seed)
    assert edge["providers"] == ["openalex", "semantic_scholar"]
    assert edge["provenance"] == [
        {"provider": provider, "observed_at": "2026-10-12T12:00:00+00:00"}
        for provider in edge["providers"]
    ]
    assert any(e["source"] == str(later) and e["target"] == str(seed) for e in graph["edges"])
    assert any(e["type"] == "related" and e["target"] == str(related) for e in graph["edges"])
    assert graph["providers"] == ["openalex", "semantic_scholar"]


def test_graph_filters_traversal_and_serialization_at_each_depth(mixed_graph):
    client, (seed, prior, later, related, distant) = mixed_graph
    params = {"seed_id": seed, "relation": "cites", "provider": "openalex", "depth": 2}
    graph = client.get("/api/graph", params=params).json()
    assert {n["id"] for n in graph["nodes"]} == {seed, prior, distant}
    assert len(graph["edges"]) == 2
    assert all(e["providers"] == ["openalex"] for e in graph["edges"])
    params["depth"] = 1
    assert {n["id"] for n in client.get("/api/graph", params=params).json()["nodes"]} == {seed, prior}
    graph = client.get("/api/graph", params={"seed_id": seed, "relation": "related", "max_nodes": 2}).json()
    assert {n["id"] for n in graph["nodes"]} == {seed, related}
    assert graph["truncated"] is False  # Exactly full is not necessarily truncated.
    incoming = client.get("/api/graph", params={"seed_id": seed, "provider": "semantic_scholar"}).json()
    assert {n["id"] for n in incoming["nodes"]} == {seed, prior, later}


def test_graph_filter_validation_unknown_provider_and_unseeded_mode(mixed_graph):
    client, (seed, *_) = mixed_graph
    assert client.get("/api/graph?relation=references").status_code == 422
    assert client.get("/api/graph?provider=").status_code == 422
    assert client.get("/api/graph", params={"provider": "x" * 81}).status_code == 422
    graph = client.get("/api/graph", params={"seed_id": seed, "provider": "' OR 1=1 --"}).json()
    assert [n["id"] for n in graph["nodes"]] == [seed]
    assert graph["edges"] == []
    graph = client.get("/api/graph", params={"relation": "related"}).json()
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["type"] == "related"
    assert graph["truncated"] is False
    assert client.get("/api/graph?max_nodes=2").json()["truncated"] is True


def test_graph_node_limit_is_deterministic_and_reports_omissions(mixed_graph):
    client, (seed, *_) = mixed_graph
    params = {"seed_id": seed, "depth": 2, "max_nodes": 2}
    graph = client.get("/api/graph", params=params).json()
    assert graph == client.get("/api/graph", params=params).json()
    assert len(graph["nodes"]) == 2
    assert graph["truncated"] is True
    ids = {str(n["id"]) for n in graph["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in graph["edges"])


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
