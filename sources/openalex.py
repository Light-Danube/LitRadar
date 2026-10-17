from __future__ import annotations

import json
import re
import urllib.parse

from .base import Paper, parse_iso_date
from .http import fetch_bytes

BASE_URL = "https://api.openalex.org/works"


def search(
    query: str,
    *,
    per_page: int = 25,
    timeout: float = 20.0,
    retries: int = 3,
    backoff: float = 1.0,
    api_key: str | None = None,
) -> list[Paper]:
    params = {"search": query, "per-page": min(max(int(per_page), 1), 100)}
    if api_key:
        params["api_key"] = api_key
    payload = _get_json(BASE_URL, params, timeout=timeout, retries=retries, backoff=backoff)
    return [_work_to_paper(item) for item in payload.get("results", []) if isinstance(item, dict)]


def fetch_neighbors(
    identifier: str,
    direction: str,
    *,
    limit: int = 25,
    timeout: float = 20.0,
    retries: int = 3,
    backoff: float = 1.0,
    api_key: str | None = None,
) -> list[Paper]:
    """Fetch one bounded citation neighborhood from OpenAlex.

    ``references`` follows the root work's ``referenced_works`` list,
    ``cited-by`` queries works whose reference lists contain the root, and
    ``related`` uses OpenAlex's curated ``related_works`` identifiers.
    """
    if direction not in {"references", "cited-by", "related"}:
        raise ValueError(f"Unsupported OpenAlex citation direction: {direction}")
    limit = min(max(int(limit), 1), 100)
    # A stored OpenAlex ID is enough for the cited-by filter: avoid an
    # unnecessary GET of the seed record before making the actual query.
    direct_id = _openalex_short_id(identifier)
    if direction == "cited-by" and direct_id:
        root_id = direct_id
        params = {
            "filter": f"cites:{root_id}",
            "per-page": limit,
            "sort": "-publication_date",
        }
        if api_key:
            params["api_key"] = api_key
        payload = _get_json(BASE_URL, params, timeout=timeout, retries=retries, backoff=backoff)
        return [_work_to_paper(item) for item in payload.get("results", []) if isinstance(item, dict)]

    root = _get_work_record(
        identifier, timeout=timeout, retries=retries, backoff=backoff, api_key=api_key
    )
    if not root:
        return []

    if direction == "cited-by":
        root_id = _openalex_short_id(root.get("id") or identifier)
        if not root_id:
            return []
        params = {
            "filter": f"cites:{root_id}",
            "per-page": limit,
            "sort": "-publication_date",
        }
        if api_key:
            params["api_key"] = api_key
        payload = _get_json(BASE_URL, params, timeout=timeout, retries=retries, backoff=backoff)
        return [_work_to_paper(item) for item in payload.get("results", []) if isinstance(item, dict)]

    field_name = "referenced_works" if direction == "references" else "related_works"
    identifiers = root.get(field_name) or []
    ids = [_openalex_short_id(value) for value in identifiers]
    ids = list(dict.fromkeys(value for value in ids if value))[:limit]
    if not ids:
        return []

    # OpenAlex supports OR-filtering up to 100 work IDs in a single request.
    params = {"filter": "openalex:" + "|".join(ids), "per-page": min(len(ids), 100)}
    if api_key:
        params["api_key"] = api_key
    payload = _get_json(BASE_URL, params, timeout=timeout, retries=retries, backoff=backoff)
    by_id = {
        _openalex_short_id(item.get("id")): item
        for item in payload.get("results", []) if isinstance(item, dict)
    }
    return [_work_to_paper(by_id[work_id]) for work_id in ids if work_id in by_id]


def _get_work_record(
    identifier: str,
    *,
    timeout: float,
    retries: int,
    backoff: float,
    api_key: str | None,
) -> dict | None:
    normalized = str(identifier or "").strip()
    short_id = _openalex_short_id(normalized)
    if short_id:
        url = f"{BASE_URL}/{urllib.parse.quote(short_id, safe='')}"
        params = {"api_key": api_key} if api_key else None
        payload = _get_json(url, params, timeout=timeout, retries=retries, backoff=backoff)
        return payload if isinstance(payload, dict) and payload.get("id") else None

    doi = normalized
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    params = {"filter": f"doi:https://doi.org/{doi}", "per-page": 1}
    if api_key:
        params["api_key"] = api_key
    payload = _get_json(BASE_URL, params, timeout=timeout, retries=retries, backoff=backoff)
    results = payload.get("results", [])
    return results[0] if results and isinstance(results[0], dict) else None


def _get_json(
    url: str,
    params: dict | None,
    *,
    timeout: float,
    retries: int,
    backoff: float,
) -> dict:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": "LitBeacon/1.0.0 (formerly LitRadar; citation intelligence)"}
    return json.loads(fetch_bytes(url, headers=headers, timeout=timeout, retries=retries, backoff=backoff))


def _openalex_short_id(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip().rstrip("/")
    text = text.rsplit("/", 1)[-1]
    return text.upper() if text[:1].casefold() == "w" and text[1:].isdigit() else None


def _work_to_paper(item: dict) -> Paper:
    primary_location = item.get("primary_location") or {}
    source = primary_location.get("source") or {}
    best_oa = item.get("best_oa_location") or {}
    doi = item.get("doi") or (item.get("ids") or {}).get("doi")
    source_tags = []
    for keyword in item.get("keywords") or []:
        value = keyword.get("display_name") if isinstance(keyword, dict) else keyword
        if value:
            source_tags.append(str(value).strip())
    identifiers = {}
    if item.get("id"):
        identifiers["openalex_id"] = str(item["id"])
    ids = item.get("ids") or {}
    for key in ("pmid", "pmcid"):
        if ids.get(key):
            identifiers[key] = str(ids[key])
    return Paper(
        source="openalex",
        title=item.get("display_name") or item.get("title") or "Untitled",
        abstract=_reconstruct_abstract(item.get("abstract_inverted_index")),
        authors=[
            (a.get("author") or {}).get("display_name", "")
            for a in item.get("authorships", [])
            if (a.get("author") or {}).get("display_name")
        ],
        published_at=parse_iso_date(item.get("publication_date")),
        doi=doi,
        url=item.get("id") or item.get("landing_page_url"),
        pdf_url=best_oa.get("pdf_url"),
        venue=source.get("display_name"),
        citation_count=int(item.get("cited_by_count") or 0),
        reference_count=int(item.get("referenced_works_count") or 0),
        external_id=item.get("id"),
        raw=item,
        source_tags=sorted(set(source_tags), key=str.casefold),
        identifiers=identifiers,
    )

def _reconstruct_abstract(inverted: dict[str, list[int]] | None) -> str:
    if not inverted:
        return ""
    words: list[tuple[int, str]] = []
    for token, positions in inverted.items():
        for pos in positions:
            words.append((pos, token))
    return " ".join(token for _, token in sorted(words))
