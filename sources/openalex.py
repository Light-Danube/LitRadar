from __future__ import annotations

import json
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
    params = {"search": query, "per-page": per_page}
    if api_key:
        params["api_key"] = api_key
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": "LitRadar/0.5.4"}
    payload = json.loads(fetch_bytes(url, headers=headers, timeout=timeout, retries=retries, backoff=backoff))

    papers: list[Paper] = []
    for item in payload.get("results", []):
        abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))
        primary_location = item.get("primary_location") or {}
        source = primary_location.get("source") or {}
        best_oa = item.get("best_oa_location") or {}
        doi = item.get("doi") or item.get("ids", {}).get("doi")
        source_tags = []
        for keyword in item.get("keywords") or []:
            value = keyword.get("display_name") if isinstance(keyword, dict) else keyword
            if value:
                source_tags.append(str(value).strip())
        papers.append(
            Paper(
                source="openalex",
                title=item.get("display_name") or item.get("title") or "Untitled",
                abstract=abstract,
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
                identifiers={"openalex_id": str(item.get("id"))} if item.get("id") else {},
            )
        )
    return papers


def _reconstruct_abstract(inverted: dict[str, list[int]] | None) -> str:
    if not inverted:
        return ""
    words: list[tuple[int, str]] = []
    for token, positions in inverted.items():
        for pos in positions:
            words.append((pos, token))
    return " ".join(token for _, token in sorted(words))
