from __future__ import annotations

import json
from pathlib import Path

from sources import openalex, semantic_scholar
from sources.base import Paper
from storage.sqlite import PaperStore


def test_openalex_parses_reference_count(monkeypatch):
    payload = {"results": [{
        "id": "https://openalex.org/W1", "display_name": "Reference Example",
        "publication_date": "2025-01-01", "referenced_works_count": 27, "cited_by_count": 13,
        "authorships": [], "abstract_inverted_index": {}, "keywords": [],
        "primary_location": {"source": {"display_name": "Venue"}},
    }]}
    monkeypatch.setattr(openalex, "fetch_bytes", lambda *a, **k: json.dumps(payload).encode())
    paper = openalex.search("test", api_key="fake")[0]
    assert paper.reference_count == 27
    assert paper.citation_count == 13


def test_semantic_scholar_parses_reference_and_influential_citation_counts(monkeypatch):
    payload = {"data": [{
        "paperId": "S1", "title": "Reference Example", "year": 2025,
        "citationCount": 101, "referenceCount": 38, "influentialCitationCount": 12,
        "authors": [{"name": "Jane Doe"}], "externalIds": {"DOI": "10.1000/example"},
        "fieldsOfStudy": ["Computer Science"],
    }]}
    monkeypatch.setattr(semantic_scholar, "fetch_bytes", lambda *a, **k: json.dumps(payload).encode())
    paper = semantic_scholar.search("test", api_key="fake")[0]
    assert paper.reference_count == 38
    assert paper.influential_citation_count == 12


def test_metrics_persist_and_migrate_into_sqlite(tmp_path: Path):
    store = PaperStore(tmp_path / "library.sqlite3")
    try:
        paper_id = store.upsert_paper(
            Paper(source="semantic_scholar", title="Metrics paper", reference_count=38, influential_citation_count=12),
            relevance_score=0.5,
            matched_groups={},
        )
        row = store.get(paper_id)
        assert row["reference_count"] == 38
        assert row["influential_citation_count"] == 12
    finally:
        store.close()
