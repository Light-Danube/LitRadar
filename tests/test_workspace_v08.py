import json
import sqlite3
import shutil
import subprocess
from pathlib import Path
from xml.etree import ElementTree

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient
from sources.base import Paper
from storage.sqlite import PaperStore
from workspace_web import create_app


@pytest.fixture
def workspace(tmp_path):
    db = tmp_path / "workspace.sqlite3"
    store = PaperStore(db)
    ids = [store.upsert_paper(Paper(source="fixture", title=f"Робота {i}", doi=f"10.1234/v08-{i}",
                                   published_at=year, abstract="Metadata evidence"),
                              relevance_score=0.8, matched_groups={})
           for i, year in enumerate(["2018-01-01", "2022-01-01", "2025-01-01", None, "unknown", "2023-01-01"])]
    for neighbor in ids[1:5]:
        store.record_relation(ids[0], neighbor, "cites", "openalex")
    store.record_relation(ids[1], ids[5], "cites", "openalex")
    store.set_notes(ids[0], "Original personal notes")
    store.close()
    return TestClient(create_app(db)), db, ids


def test_year_filter_applies_before_traversal_and_keeps_seed(workspace):
    client, _, (seed, prior, later, missing, invalid, second) = workspace
    params = {"seed_id": seed, "year_from": 2020, "year_to": 2024, "include_unknown": False, "depth": 2}
    graph = client.get("/api/graph", params=params).json()
    assert {n["id"] for n in graph["nodes"]} == {seed, prior, second}
    assert len(graph["edges"]) == 2
    params["include_unknown"] = True
    assert {n["id"] for n in client.get("/api/graph", params=params).json()["nodes"]} == {seed, prior, second, missing, invalid}
    params["max_nodes"] = 3
    params["include_unknown"] = False
    graph = client.get("/api/graph", params=params).json()
    assert graph["truncated"] is False
    assert len(graph["nodes"]) == 3
    assert later not in {n["id"] for n in graph["nodes"]}


def test_unseeded_year_filter_and_validation(workspace):
    client, _, ids = workspace
    graph = client.get("/api/graph", params={"year_from": 2022, "year_to": 2023, "include_unknown": False}).json()
    assert {n["id"] for n in graph["nodes"]} == {ids[1], ids[5]}
    assert graph["year_from"] == 2022 and graph["include_unknown"] is False
    assert client.get("/api/graph?year_from=2024&year_to=2020").status_code == 422
    assert client.get("/api/graph?year_to=99").status_code == 422
    assert client.get("/api/graph?year_from=no").status_code == 422


def test_localized_assets_are_served_and_html_is_not_cached(workspace):
    client, _, _ = workspace
    page = client.get("/")
    assert page.headers["cache-control"] == "no-store"
    assert 'id="language"' in page.text and 'id="skip-link"' in page.text
    assert page.text.index('/static/locales.js') < page.text.index('/static/app.js')
    assert page.text.index('/static/graph-tools.js') < page.text.index('/static/app.js')
    assert client.get('/static/locales.js').status_code == 200
    assert 'Дослідницький простір' in client.get('/static/locales.js').text
    assert client.get('/static/graph-tools.js').status_code == 200


def test_import_is_atomic_idempotent_and_assigns_provenance(workspace):
    client, db, (paper_id, *_) = workspace
    url = f"/api/papers/{paper_id}/annotations/import"
    payload = {"filename": "нотатки.json", "items": [{"content": "Український матеріал", "source_ref": "p. 3"}]}
    first = client.post(url, json=payload)
    assert first.status_code == 200
    item = first.json()["items"][0]
    assert item["kind"] == "imported" and item["origin_method"] == "json_import"
    assert "нотатки.json" in item["source_ref"]
    assert client.post(url, json=payload).json()["added"] == 0
    invalid = {"filename": "bad.json", "items": [{"content": "Valid first item"}, {"content": " "}]}
    assert client.post(url, json=invalid).status_code == 422
    store = PaperStore(db)
    assert len(store.list_annotations(paper_id)) == 1
    assert store.get(paper_id)["notes"] == "Original personal notes"
    store.close()
    spoof = {"filename": "spoof.json", "items": [{"content": "x", "kind": "generated"}]}
    assert client.post(url, json=spoof).status_code == 422


def test_extraction_generation_is_opt_in_and_retains_reviewed_edits(workspace):
    client, db, (paper_id, *_) = workspace
    url = f"/api/papers/{paper_id}/annotations/extract"
    result = client.post(url, json={}).json()
    assert [item["kind"] for item in result["items"]] == ["extracted"]
    assert json.loads(result["items"][0]["content"])["abstract_excerpt"] == "Metadata evidence"
    assert client.post(url, json={}).json()["added"] == 0
    result = client.post(url, json={"include_generated": True, "language": "uk"}).json()
    generated = next(item for item in result["items"] if item["kind"] == "generated")
    assert generated["origin_method"] == "local_heuristic"
    assert "Перевірте" in generated["content"]
    patch_url = f"/api/papers/{paper_id}/annotations/{generated['id']}"
    edited = client.patch(patch_url, json={"expected_revision": 1, "content": "Edited by reader", "review_status": "accepted"}).json()
    assert edited["revision"] == 2 and edited["updated_at"]
    assert edited["kind"] == generated["kind"] and edited["source_ref"] == generated["source_ref"]
    repeat = client.post(url, json={"include_generated": True, "language": "uk"}).json()
    assert repeat["added"] == 0
    assert next(item for item in repeat["items"] if item["kind"] == "generated")["content"] == "Edited by reader"
    assert client.patch(patch_url, json={"expected_revision": 1, "content": "Stale"}).status_code == 409
    store = PaperStore(db)
    revisions = store.conn.execute("SELECT * FROM annotation_revisions WHERE annotation_id=? ORDER BY revision", (generated["id"],)).fetchall()
    assert [row["content"] for row in revisions] == [generated["content"], "Edited by reader"]
    assert store.get(paper_id)["notes"] == "Original personal notes"
    store.close()


def test_stored_assessment_provenance_and_failed_extraction_roll_back(workspace):
    client, db, (paper_id, *_) = workspace
    store = PaperStore(db)
    assessment = {"summary": "Existing model summary", "provider": "ollama", "model": "fixture-model", "suggested_tags": ["context"]}
    store.conn.execute("UPDATE papers SET llm_assessment_json=? WHERE id=?", (json.dumps(assessment), paper_id))
    store.conn.commit(); store.close()
    url = f"/api/papers/{paper_id}/annotations/extract"
    generated = client.post(url, json={"include_generated": True}).json()["items"][1]
    assert generated["origin_method"] == "stored_assessment"
    assert "fixture-model" in generated["source_ref"]
    assert json.loads(generated["content"])["summary"] == assessment["summary"]
    store = PaperStore(db)
    count = len(store.list_annotations(paper_id))
    assessment["summary"] = "x" * 50001
    store.conn.execute("UPDATE papers SET abstract='New snapshot', llm_assessment_json=? WHERE id=?", (json.dumps(assessment), paper_id))
    store.conn.commit();store.close()
    assert client.post(url, json={"include_generated": True}).status_code == 422
    store = PaperStore(db)
    assert len(store.list_annotations(paper_id)) == count
    store.close()


def test_review_note_history_and_missing_or_invalid_requests(workspace):
    client, _, (paper_id, other, *_) = workspace
    url = f"/api/papers/{paper_id}/annotations"
    item = client.post(url, json={"content": "Review this"}).json()
    path = f"{url}/{item['id']}"
    assert client.patch(path, json={"expected_revision": 1, "review_status": "dismissed"}).json()["revision"] == 2
    assert client.patch(path, json={"expected_revision": 2, "review_status": "dismissed"}).json()["revision"] == 2
    assert client.patch(path, json={"expected_revision": 2, "review_status": "unreviewed"}).json()["revision"] == 3
    assert client.patch(path, json={"expected_revision": 3, "kind": "user"}).status_code == 422
    assert client.patch(path, json={"expected_revision": 3, "content": " "}).status_code == 422
    assert client.patch(f"/api/papers/{other}/annotations/{item['id']}", json={"expected_revision": 3}).status_code == 404
    client.patch(f"/api/papers/{paper_id}", json={"notes": "Latest note"})
    client.patch(f"/api/papers/{paper_id}", json={"notes": ""})
    history = client.get(f"/api/papers/{paper_id}/notes/history?limit=2").json()
    assert [row["content"] for row in history["items"]] == ["", "Latest note"]
    assert history["next_before_id"]
    older = client.get(f"/api/papers/{paper_id}/notes/history", params={"before_id": history["next_before_id"]}).json()
    assert older["items"][0]["content"] == "Original personal notes"
    note_id = history["items"][0]["id"]
    assert client.patch(f"{url}/{note_id}", json={"expected_revision": 1, "content": "Cannot edit history"}).status_code == 404
    assert client.get("/api/papers/999/notes/history").status_code == 404
    assert client.post("/api/papers/999/annotations/extract", json={}).status_code == 404


def test_previous_annotation_schema_migrates_without_losing_entries(workspace):
    _, db, (paper_id, *_) = workspace
    conn = sqlite3.connect(db)
    conn.executescript("DROP TABLE annotation_revisions; DROP TABLE paper_annotations; "
                      "CREATE TABLE paper_annotations(id INTEGER PRIMARY KEY AUTOINCREMENT, paper_id INTEGER, "
                      "channel TEXT, kind TEXT, content TEXT, source_ref TEXT, recorded_at TEXT);")
    conn.execute("INSERT INTO paper_annotations VALUES(1, ?, 'annotation', 'imported', 'Old import', 'file.pdf', '2026-01-01')", (paper_id,))
    conn.commit();conn.close()
    store = PaperStore(db)
    item = dict(store.list_annotations(paper_id)[0])
    assert item["content"] == "Old import" and item["source_ref"] == "file.pdf"
    assert item["origin_method"] == "declared" and item["revision"] == 1
    assert store.conn.execute("SELECT COUNT(*) FROM annotation_revisions").fetchone()[0] == 1
    store.close()
    store = PaperStore(db)
    assert store.conn.execute("SELECT COUNT(*) FROM annotation_revisions").fetchone()[0] == 1
    store.close()


def test_export_xml_is_well_formed_and_preserves_unicode_and_direction(workspace):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is optional locally; the web CI job installs it")
    client, _, ids = workspace
    graph = client.get("/api/graph", params={"seed_id": ids[0]}).json()
    graph["nodes"][0]["title"] = "Українська <script> & title"
    module = Path(__file__).resolve().parents[1] / "web/static/graph-tools.js"
    script = "const fs=require('fs'),g=require(process.argv[1]),data=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify({svg:g.svg(data),graphml:g.graphml(data)}));"
    exported = json.loads(subprocess.check_output([node, "-e", script, str(module)], input=json.dumps(graph).encode()))
    svg = ElementTree.fromstring(exported["svg"])
    ns = {"s": "http://www.w3.org/2000/svg", "g": "http://graphml.graphdrawing.org/xmlns"}
    assert len(svg.findall(".//s:g", ns)) == len(graph["nodes"])
    assert not svg.findall(".//s:script", ns)
    assert "Українська <script> & title" in [item.text for item in svg.findall(".//s:title", ns)]
    graphml = ElementTree.fromstring(exported["graphml"])
    edges = graphml.findall(".//g:edge", ns)
    assert len(edges) == len(graph["edges"])
    assert all(edge.attrib["directed"] == "true" for edge in edges)
