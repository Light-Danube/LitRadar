"""Explicit, bounded venue discovery using the existing library connection."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import urllib.error

from config import RadarConfig
from sources.base import Paper
from sources import venues
from storage.sqlite import PaperStore


def _http(config: RadarConfig) -> dict:
    return dict(timeout=min(config.source_timeout, 60), retries=min(config.source_retries, 3),
                backoff=min(config.source_backoff, 5), api_key=config.openalex_api_key)


def save_venue(store: PaperStore, venue) -> None:
    store.conn.execute(
        "INSERT INTO discovery_venues VALUES (?, ?, ?) ON CONFLICT(source_id) DO UPDATE SET "
        "metadata_json=excluded.metadata_json, retrieved_at=excluded.retrieved_at",
        (venue.source_id, json.dumps(asdict(venue), ensure_ascii=False), venue.retrieved_at),
    )


def lookup(store: PaperStore, query: str, *, limit=10, config: RadarConfig | None = None):
    found = venues.lookup_venues(query, limit=limit, **_http(config or RadarConfig()))
    with store.conn:
        for venue in found:
            save_venue(store, venue)
    return found


def search_and_store(store: PaperStore, query: str, source_id: str, *, year_from=None,
                     year_to=None, limit=20, page=1, config: RadarConfig | None = None,
                     force=False) -> dict:
    """One page only; cached pages retain their original observation timestamps."""
    config = config or RadarConfig()
    source_id = venues.normalize_source_id(source_id)
    if not isinstance(query, str) or not query.strip() or len(query) > 500:
        raise ValueError("Query must contain 1–500 characters")
    if not 1 <= limit <= 100 or not 1 <= page <= 10:
        raise ValueError("Limit must be 1–100 and page 1–10")
    if any(y is not None and (isinstance(y, bool) or not isinstance(y, int) or not 1000 <= y <= 9999)
           for y in (year_from, year_to)):
        raise ValueError("Years must be 1000–9999")
    if year_from is not None and year_to is not None and year_from > year_to:
        raise ValueError("Year bounds must be ordered")
    key_data = ["openalex", source_id, query.strip(), year_from, year_to, limit, page]
    key = hashlib.sha256(json.dumps(key_data).encode()).hexdigest()
    cached = store.conn.execute("SELECT * FROM venue_search_cache WHERE cache_key=?", (key,)).fetchone()
    payload = None
    if cached and not force and config.source_cache_ttl > 0:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(cached["retrieved_at"])).total_seconds()
        if 0 <= age < config.source_cache_ttl:
            payload = json.loads(cached["payload_json"])
    cache_hit = payload is not None
    if payload is None:
        result = venues.search_venue(query.strip(), source_id, year_from=year_from, year_to=year_to,
                                     limit=limit, page=page, **_http(config))
        payload = result.to_dict()
    venue = venues.Venue(**payload["venue"])
    papers = [Paper(**item) for item in payload["papers"]]
    ids = []
    before = store.total_count()
    with store.conn:
        save_venue(store, venue)
        for paper in papers:
            existing_id = store.find_existing_paper_id(paper)
            row = store.get(existing_id) if existing_id is not None else None
            paper_id = store._upsert_paper_no_commit(
                paper, relevance_score=float(row["relevance_score"]) if row else 0,
                matched_groups=json.loads(row["matched_groups_json"]) if row else {},
                keyword_score=float(row["keyword_score"]) if row else 0,
                semantic_score=row["semantic_score"] if row else None,
                scoring_version=row["scoring_version"] if row else "venue-unranked",
            )
            observation = dict(payload["provenance"], original_venue=paper.venue,
                               provider="openalex", venue=payload["venue"])
            store.conn.execute(
                "INSERT INTO paper_venue_observations VALUES (?, ?, ?) "
                "ON CONFLICT(paper_id, source_id) DO UPDATE SET observation_json=excluded.observation_json",
                (paper_id, venue.source_id, json.dumps(observation, ensure_ascii=False)),
            )
            ids.append(paper_id)
        if not cache_hit:
            store.conn.execute(
                "INSERT INTO venue_search_cache VALUES (?, ?, ?) ON CONFLICT(cache_key) DO UPDATE SET "
                "retrieved_at=excluded.retrieved_at, payload_json=excluded.payload_json",
                (key, datetime.now(timezone.utc).isoformat(), json.dumps(payload, ensure_ascii=False)),
            )
            # Keep optional discovery cache bounded without touching library data.
            store.conn.execute("DELETE FROM venue_search_cache WHERE cache_key IN "
                               "(SELECT cache_key FROM venue_search_cache ORDER BY retrieved_at DESC LIMIT -1 OFFSET 100)")
    return dict(payload, paper_ids=ids, cache_hit=cache_hit,
                newly_stored=store.total_count() - before,
                status="ok" if papers else "zero_results")


def error_status(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        if exc.code == 429:
            return "rate_limited"
        if exc.code in {401, 403, 404}:
            return "metadata_inaccessible"
        return "provider_error"
    if isinstance(exc, TimeoutError) or (isinstance(exc, urllib.error.URLError)
                                         and isinstance(exc.reason, TimeoutError)):
        return "timeout"
    if isinstance(exc, urllib.error.URLError) or isinstance(exc, OSError):
        return "network_unavailable"
    if isinstance(exc, venues.VenueMetadataError):
        return "malformed_metadata"
    return "invalid_request"
