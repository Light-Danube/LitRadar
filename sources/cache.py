from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict
from pathlib import Path

from .base import Paper

from litradar_runtime import DATA_ROOT

DEFAULT_CACHE_DIR = DATA_ROOT / "source_cache"


def cache_path(source: str, query: str, per_source: int, cache_dir: str | Path = DEFAULT_CACHE_DIR) -> Path:
    key = f"{source}|{per_source}|{query.casefold()}".encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()
    return Path(cache_dir) / source / f"{digest}.json"


def load_cached(source: str, query: str, per_source: int, ttl: int, cache_dir: str | Path = DEFAULT_CACHE_DIR) -> list[Paper] | None:
    if ttl <= 0:
        return None
    path = cache_path(source, query, per_source, cache_dir)
    try:
        if time.time() - path.stat().st_mtime > ttl:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [Paper(**item) for item in payload.get("papers", [])]
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def save_cached(source: str, query: str, per_source: int, papers: list[Paper], cache_dir: str | Path = DEFAULT_CACHE_DIR) -> None:
    path = cache_path(source, query, per_source, cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"source": source, "query": query, "per_source": per_source, "saved_at": time.time(), "papers": [asdict(paper) for paper in papers]}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
    os.replace(tmp, path)
