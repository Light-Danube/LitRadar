"""Cross-platform API workflow using only a disposable library."""
import pytest

pytest.importorskip("fastapi", reason="optional browser workspace dependency")
pytest.importorskip("httpx", reason="optional TestClient dependency")
from fastapi.testclient import TestClient
from sources.base import Paper
from storage.sqlite import PaperStore
from workspace_web import create_app


def test_inbox_edit_cluster_and_graph_navigation_roundtrip(tmp_path):
    db = tmp_path / "synthetic-workspace.sqlite3"
    store = PaperStore(db)
    try:
        ids = [store.upsert_paper(Paper(source=provider, title=title, doi=f"10.1234/smoke-{index}", published_at="2024", abstract="Synthetic context research"), relevance_score=.5, matched_groups={}) for index, (provider, title) in enumerate([("openalex", "Synthetic seed — Дослідження"), ("semantic_scholar", "Synthetic prior")])]
        for provider in ["openalex", "semantic_scholar"]:
            store.record_relation(ids[0], ids[1], "cites", provider)
            store.record_relation(ids[1], ids[0], "cites", provider)
        store.set_tags(ids[1], ["shared"])
    finally:
        store.close()
    seed, prior = ids
    with TestClient(create_app(db)) as client:
        results = client.get("/api/papers", params={"q": "Дослідження", "status": "new"}).json()
        assert [p["id"] for p in results["items"]] == [seed]
        saved = client.patch(f"/api/papers/{seed}", json={"status": "to-read", "tags": ["shared", "українська"], "notes": "Synthetic note — примітка"})
        assert saved.status_code == 200
        assert client.get("/api/papers", params={"status": "new", "q": "Дослідження"}).json()["count"] == 0
        item = client.get(f"/api/papers/{seed}").json()
        assert item["notes"] == "Synthetic note — примітка" and item["status"] == "to-read"
        history = client.get(f"/api/papers/{seed}/notes/history").json()["items"]
        assert history[0]["content"] == item["notes"]
        clusters = client.get("/api/clusters").json()
        shared = next(c for c in clusters["clusters"] if c["label"] == "Tag · shared")
        assert {p["id"] for p in shared["papers"]} == {seed, prior}
        for selected in [seed, prior]:
            graph = client.get("/api/graph", params={"seed_id": selected, "depth": 1}).json()
            assert {p["id"] for p in graph["nodes"]} == {seed, prior}
            assert {(e["source"], e["target"]) for e in graph["edges"]} == {(str(seed), str(prior)), (str(prior), str(seed))}
            assert all(e["providers"] == ["openalex", "semantic_scholar"] for e in graph["edges"])
            filtered = client.get("/api/graph", params={"seed_id": selected, "provider": "semantic_scholar"}).json()
            assert len(filtered["edges"]) == 2 and all(e["providers"] == ["semantic_scholar"] for e in filtered["edges"])
