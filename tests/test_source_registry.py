from __future__ import annotations

import time
from pathlib import Path

from config import RadarConfig
from sources.base import Paper
from sources.registry import SourceDefinition, SourceRegistry, search_all_sources


def _paper(source: str) -> Paper:
    return Paper(source=source, title=f"Paper from {source}")


def _config(tmp_path: Path, workers: int = 3) -> RadarConfig:
    # Explicit construction keeps tests independent from a developer's .env.
    return RadarConfig(
        enabled_sources=("a", "b", "c"),
        source_workers=workers,
        source_timeout=1.0,
        source_retries=0,
        source_backoff=0.0,
        source_cache_ttl=0,
        personalization_min_feedback=5,
    )


def test_registry_runs_sources_concurrently(tmp_path):
    def make_search(name: str):
        def search(_query: str, _limit: int, _config: RadarConfig):
            time.sleep(0.12)
            return [_paper(name)]

        return search

    registry = SourceRegistry([
        SourceDefinition("a", make_search("a")),
        SourceDefinition("b", make_search("b")),
        SourceDefinition("c", make_search("c")),
    ])
    started = time.perf_counter()
    results, errors = search_all_sources("x", config=_config(tmp_path, workers=3), registry=registry)
    elapsed = time.perf_counter() - started
    assert not errors
    assert set(results) == {"a", "b", "c"}
    # Sequential execution would be ~0.36s; allow CI variability.
    assert elapsed < 0.30


def test_registry_isolates_one_source_failure(tmp_path):
    def good(_query, _limit, _config):
        return [_paper("good")]

    def bad(_query, _limit, _config):
        raise RuntimeError("boom")

    registry = SourceRegistry([
        SourceDefinition("good", good),
        SourceDefinition("bad", bad),
    ])
    config = RadarConfig(
        enabled_sources=("good", "bad"),
        source_workers=2,
        source_timeout=1.0,
        source_retries=0,
        source_backoff=0.0,
        source_cache_ttl=0,
    )
    results, errors = search_all_sources("x", config=config, registry=registry)
    assert results["good"][0].source == "good"
    assert isinstance(errors["bad"], RuntimeError)


def test_unknown_source_fails_fast(tmp_path):
    registry = SourceRegistry([SourceDefinition("good", lambda *_: [])])
    config = RadarConfig(enabled_sources=("missing",), source_cache_ttl=0)
    try:
        search_all_sources("x", config=config, registry=registry)
    except ValueError as exc:
        assert "Unknown source" in str(exc)
    else:
        raise AssertionError("Expected unknown source ValueError")
