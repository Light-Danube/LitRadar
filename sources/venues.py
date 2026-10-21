"""Opt-in, bounded OpenAlex source lookup and venue-scoped retrieval.

Provider metadata verifies an identity, never peer review or index membership.
HTTP errors deliberately retain the shared adapter's original exception types.
Documented endpoints and structured filters:
https://docs.openalex.org/api-entities/sources/search-sources
https://docs.openalex.org/api-entities/works/filter-works#primary_location.source.id
https://docs.openalex.org/api-entities/works/filter-works#publication_year
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import re
from typing import Any
import urllib.parse

from . import openalex
from .base import Paper
from .filters import normalize_metadata_language

SOURCES_URL = "https://api.openalex.org/sources"
MAX_LIMIT = 100
MAX_PAGE = 100


class VenueMetadataError(ValueError):
    """A provider response is malformed or contradicts the requested identity."""


@dataclass(frozen=True, slots=True)
class Venue:
    source_id: str
    display_name: str
    venue_type: str
    issn_l: str | None
    issns: tuple[str, ...]
    publisher: str | None
    record_url: str
    retrieved_at: str
    lookup_query: str = ""
    provider: str = "openalex"
    verification_status: str = "provider_metadata"
    peer_review_status: str = "unverified"
    scopus_status: str = "unverified"
    wos_status: str = "unverified"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class VenueSearchResult:
    venue: Venue
    papers: list[Paper]
    count: int
    truncated: bool
    page: int
    limit: int
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_source_id(value: str) -> str:
    """Accept a concrete source ID or its exact public OpenAlex URL only."""
    text = str(value).strip()
    if text.startswith("https://openalex.org/"):
        text = text[len("https://openalex.org/"):]
    if not re.fullmatch(r"S[0-9]+", text, flags=re.IGNORECASE):
        raise ValueError("Select a concrete OpenAlex source ID (S followed by digits)")
    return text.upper()


def _bounded(value: int, maximum: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be an integer between 1 and {maximum}")
    return value


def _query(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 1000:
        raise ValueError("Query must contain 1–1000 characters")
    return value.strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get(url: str, params: dict[str, Any], *, timeout: float, retries: int,
         backoff: float, api_key: str | None) -> dict[str, Any]:
    if (not isinstance(timeout, (int, float)) or isinstance(timeout, bool)
            or not 0 < timeout <= 120 or not isinstance(retries, int) or isinstance(retries, bool)
            or not 0 <= retries <= 5 or not isinstance(backoff, (int, float))
            or isinstance(backoff, bool) or not 0 <= backoff <= 30):
        raise ValueError("HTTP bounds: timeout 0–120 seconds, retries 0–5, backoff 0–30")
    request_params = dict(params)
    if api_key:
        request_params["api_key"] = api_key
    try:
        payload = openalex._get_json(url, request_params, timeout=timeout, retries=retries, backoff=backoff)
    except json.JSONDecodeError as exc:
        raise VenueMetadataError("OpenAlex returned malformed JSON") from exc
    if not isinstance(payload, dict):
        raise VenueMetadataError("OpenAlex response must be an object")
    return payload


def _source(record: Any, *, query: str = "", expected_id: str | None = None) -> Venue:
    if not isinstance(record, dict):
        raise VenueMetadataError("OpenAlex source record must be an object")
    try:
        source_id = normalize_source_id(record.get("id", ""))
    except ValueError as exc:
        raise VenueMetadataError("OpenAlex source record has no valid source identity") from exc
    name = record.get("display_name")
    if not isinstance(name, str) or not name.strip():
        raise VenueMetadataError("OpenAlex source record has no display name")
    if expected_id and source_id != expected_id:
        raise VenueMetadataError("OpenAlex returned a different source identity")
    issns = record.get("issn")
    if issns is None:
        issns = []
    issn_l = record.get("issn_l")
    publisher = record.get("host_organization_name")
    if not isinstance(issns, list) or any(not isinstance(item, str) for item in issns):
        raise VenueMetadataError("OpenAlex source ISSNs must be a list of strings")
    if issn_l is not None and not isinstance(issn_l, str):
        raise VenueMetadataError("OpenAlex source ISSN-L must be a string or null")
    if publisher is not None and not isinstance(publisher, str):
        raise VenueMetadataError("OpenAlex host organization name must be a string or null")
    source_type = record.get("type")
    if source_type is not None and not isinstance(source_type, str):
        raise VenueMetadataError("OpenAlex source type must be a string or null")
    venue_type = {
        "journal": "journal", "conference": "conference/proceedings",
        "repository": "repository/preprint", "book series": "book series",
        "hosting platform": "hosting platform", "platform": "hosting platform",
    }.get(source_type, "unknown")
    return Venue(source_id=source_id, display_name=name, venue_type=venue_type,
                 issn_l=issn_l, issns=tuple(issns), publisher=publisher,
                 record_url=f"{SOURCES_URL}/{source_id}", retrieved_at=_utc_now(), lookup_query=query)


def _results(payload: dict[str, Any], limit: int) -> list[Any]:
    results = payload.get("results")
    if not isinstance(results, list) or len(results) > limit:
        raise VenueMetadataError("OpenAlex results must be a bounded list")
    return results


def lookup_venues(query: str, *, limit: int = 10, timeout: float = 20,
                  retries: int = 2, backoff: float = 1, api_key: str | None = None) -> list[Venue]:
    query = _query(query)
    limit = _bounded(limit, MAX_LIMIT, "limit")
    payload = _get(SOURCES_URL, {"search": query, "per-page": limit}, timeout=timeout,
                   retries=retries, backoff=backoff, api_key=api_key)
    return [_source(item, query=query) for item in _results(payload, limit)]


def get_venue(source_id: str, *, timeout: float = 20, retries: int = 2,
              backoff: float = 1, api_key: str | None = None) -> Venue:
    source_id = normalize_source_id(source_id)
    payload = _get(f"{SOURCES_URL}/{source_id}", {}, timeout=timeout, retries=retries,
                   backoff=backoff, api_key=api_key)
    return _source(payload, expected_id=source_id)


def _validated_work(item: Any, source_id: str, year_from: int | None, year_to: int | None) -> Paper:
    if not isinstance(item, dict):
        raise VenueMetadataError("OpenAlex work must be an object")
    location = item.get("primary_location")
    source = location.get("source") if isinstance(location, dict) else None
    try:
        actual_source = normalize_source_id(source.get("id", "")) if isinstance(source, dict) else None
    except ValueError as exc:
        raise VenueMetadataError("OpenAlex work has an invalid venue identity") from exc
    if actual_source != source_id:
        raise VenueMetadataError("OpenAlex work contradicts the selected venue filter")
    year = item.get("publication_year")
    if year_from is not None or year_to is not None:
        if isinstance(year, bool) or not isinstance(year, int):
            raise VenueMetadataError("OpenAlex work has no valid publication year")
        if (year_from is not None and year < year_from) or (year_to is not None and year > year_to):
            raise VenueMetadataError("OpenAlex work contradicts the selected year filter")
    try:
        for field in ("ids", "best_oa_location", "abstract_inverted_index"):
            if item.get(field) is not None and not isinstance(item[field], dict):
                raise ValueError(f"invalid {field}")
        for field in ("doi", "publication_date", "landing_page_url"):
            if item.get(field) is not None and not isinstance(item[field], str):
                raise ValueError(f"invalid {field}")
        for field in ("keywords", "authorships"):
            if item.get(field) is not None and not isinstance(item[field], list):
                raise ValueError(f"invalid {field}")
        if not re.fullmatch(r"(?:https://openalex.org/)?W[0-9]+", str(item.get("id", ""))):
            raise ValueError("missing work ID")
        title = item.get("display_name") or item.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("missing title")
        paper = openalex._work_to_paper(item)
        # The shared parser assumes valid API data; validate values it passes through.
        if any(not isinstance(value, str) for value in paper.authors):
            raise ValueError("invalid author")
        if paper.doi is not None and not isinstance(paper.doi, str):
            raise ValueError("invalid DOI")
        if paper.venue is not None and not isinstance(paper.venue, str):
            raise ValueError("invalid venue name")
        return paper
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError) as exc:
        raise VenueMetadataError("Malformed OpenAlex work metadata") from exc


def validate_search(query: str, source_id: str, *, year_from: int | None = None,
                    year_to: int | None = None, limit: int = 20, page: int = 1) -> tuple[str, str]:
    """Validate cache keys before consulting cached or online metadata."""
    query = _query(query)
    source_id = normalize_source_id(source_id)
    limit = _bounded(limit, MAX_LIMIT, "limit")
    page = _bounded(page, MAX_PAGE, "page")
    for year in (year_from, year_to):
        if year is not None and (isinstance(year, bool) or not isinstance(year, int) or not 1 <= year <= 9999):
            raise ValueError("Year must be an integer between 1 and 9999")
    if year_from is not None and year_to is not None and year_from > year_to:
        raise ValueError("year_from must not exceed year_to")
    return query, source_id


def search_venue(query: str, source_id: str, *, year_from: int | None = None,
                 year_to: int | None = None, limit: int = 20, page: int = 1,
                 timeout: float = 20, retries: int = 2, backoff: float = 1,
                 api_key: str | None = None, metadata_language: str = "any") -> VenueSearchResult:
    metadata_language = normalize_metadata_language(metadata_language)
    query, source_id = validate_search(query, source_id, year_from=year_from,
                                       year_to=year_to, limit=limit, page=page)
    venue = get_venue(source_id, timeout=timeout, retries=retries, backoff=backoff, api_key=api_key)
    filters = [f"primary_location.source.id:{source_id}"]
    if metadata_language != "any":
        filters.append(f"language:{metadata_language}")
    if year_from is not None or year_to is not None:
        filters.append(f"publication_year:{year_from or 1}-{year_to or 9999}")
    params = {"search": query, "filter": ",".join(filters), "per-page": limit, "page": page}
    payload = _get(openalex.BASE_URL, params, timeout=timeout, retries=retries, backoff=backoff, api_key=api_key)
    meta = payload.get("meta")
    count = meta.get("count") if isinstance(meta, dict) else None
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise VenueMetadataError("OpenAlex result count must be a nonnegative integer")
    items = _results(payload, limit)
    if count < (page - 1) * limit + len(items) and items:
        raise VenueMetadataError("OpenAlex result count contradicts returned page")
    papers = [_validated_work(item, source_id, year_from, year_to) for item in items]
    try:
        openalex.validate_language_results(papers, metadata_language)
    except ValueError as exc:
        raise VenueMetadataError("OpenAlex response contradicts the metadata-language filter") from exc
    provenance = {"provider": "openalex", "source_id": source_id,
                  "record_url": f"{openalex.BASE_URL}?{urllib.parse.urlencode(params)}",
                  "retrieved_at": _utc_now(), "query": query, "year_from": year_from,
                  "year_to": year_to, "filter": params["filter"], "verification_status": "provider_metadata",
                  "peer_review_status": "unverified", "scopus_status": "unverified", "wos_status": "unverified"}
    if metadata_language != "any":
        provenance.update(metadata_language=metadata_language,
                          language_basis="openalex_detected_title_abstract")
    return VenueSearchResult(venue, papers, count, count > (page - 1) * limit + len(papers), page, limit, provenance)
