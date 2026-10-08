from __future__ import annotations

from pathlib import Path

import sources.registry as registry_module
from config import RadarConfig
from sources.base import Paper
from sources.registry import SourceDefinition, SourceRegistry, search_all_sources


def test_registry_uses_cache_without_second_source_call(tmp_path, monkeypatch):
    calls = {"n": 0}

    def search(_query, _limit, _config):
        calls["n"] += 1
        return [Paper(source="fake", title="Cached once")]

    source = SourceDefinition("fake", search)
    registry = SourceRegistry([source])
    cache_dir = tmp_path / "cache"
    config = RadarConfig(
        enabled_sources=("fake",),
        source_workers=1,
        source_timeout=1.0,
        source_retries=0,
        source_backoff=0.0,
        source_cache_ttl=3600,
    )
    monkeypatch.setattr(registry_module, "default_registry", lambda: registry)
    monkeypatch.setattr(registry_module, "load_cached", lambda source_name, query, limit, ttl: None if calls["n"] == 0 else [Paper(source="fake", title="Cached once")])
    monkeypatch.setattr(registry_module, "save_cached", lambda *args, **kwargs: None)
    first, _ = search_all_sources("cache me", config=config, registry=registry)
    second, _ = search_all_sources("cache me", config=config, registry=registry)
    assert calls["n"] == 1
    assert first["fake"][0].title == second["fake"][0].title
