from __future__ import annotations

import json
from pathlib import Path

import pipeline
from config import RadarConfig
from sources.base import Paper
from sources.registry import SourceDefinition, SourceRegistry, search_all_sources


def test_source_registry_emits_progress_for_each_provider(tmp_path: Path):
    events = []
    config = RadarConfig(
        enabled_sources=("fake",), source_workers=1, source_timeout=1,
        source_retries=0, source_backoff=0, source_cache_ttl=0,
    )
    registry = SourceRegistry([SourceDefinition("fake", lambda q, n, c: [Paper(source="fake", title="Progress paper")])])
    results, errors = search_all_sources("progress test", config=config, registry=registry, progress=lambda *event: events.append(event))
    assert not errors
    assert len(results["fake"]) == 1
    assert [event[0] for event in events] == ["started", "completed"]
    assert "received 1 papers" in events[-1][2]


def test_pipeline_reports_added_and_library_totals(tmp_path: Path, monkeypatch):
    db = tmp_path / "library.sqlite3"
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({
        "name": "test",
        "description": "context selection",
        "ranking": {"keyword_weight": 1.0, "semantic_weight": 0.0},
        "groups": [{"name": "context", "weight": 2, "terms": ["context"]}],
    }), encoding="utf-8")
    config = RadarConfig(enabled_sources=("fake",), source_cache_ttl=0)
    paper = Paper(source="fake", title="Context Selection Paper", abstract="Context selection for a test.")
    monkeypatch.setattr(pipeline, "search_all_sources", lambda *a, **k: ({"fake": [paper]}, {}))

    first, ranked = pipeline.search_and_ingest("context", db_path=db, profile_path=profile, semantic=False, config=config)
    second, _ = pipeline.search_and_ingest("context", db_path=db, profile_path=profile, semantic=False, config=config)
    assert first.fetched == 1
    assert first.newly_stored == 1
    assert first.library_total == 1
    assert first.source_results == {"fake": 1}
    assert ranked[0][0].title == paper.title
    assert second.fetched == 1
    assert second.newly_stored == 0
    assert second.library_total == 1
