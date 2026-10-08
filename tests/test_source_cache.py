from __future__ import annotations

from pathlib import Path

from sources.base import Paper
from sources.cache import load_cached, save_cached


def test_source_cache_roundtrip(tmp_path: Path):
    papers = [Paper(source="arxiv", title="Cached paper", identifiers={"arxiv_id": "2501.12345"})]
    save_cached("arxiv", "context sarcasm", 5, papers, tmp_path)
    loaded = load_cached("arxiv", "context sarcasm", 5, 3600, tmp_path)
    assert loaded is not None
    assert loaded[0].title == "Cached paper"
    assert loaded[0].identifiers["arxiv_id"] == "2501.12345"
