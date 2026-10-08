from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from .base import Paper, parse_iso_date

BASE_URL = "https://api.openalex.org/works"


def search(query: str, *, per_page: int = 25) -> list[Paper]:
    params = urllib.parse.urlencode({"search": query, "per-page": per_page})
    url = f"{BASE_URL}?{params}"
    headers = {"User-Agent": "LitRadar/0.3"}
    mailto = os.getenv("LITRADAR_MAILTO")
    if mailto:
        headers["From"] = mailto
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)

    papers: list[Paper] = []
    for item in payload.get("results", []):
        abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))
        primary_location = item.get("primary_location") or {}
        source = primary_location.get("source") or {}
        best_oa = item.get("best_oa_location") or {}
        doi = item.get("doi") or item.get("ids", {}).get("doi")
        source_tags = []
        for keyword in item.get("keywords") or []:
            if isinstance(keyword, dict):
                value = keyword.get("display_name") or keyword.get("keyword")
            else:
                value = keyword
            if value:
                source_tags.append(str(value).strip())
        papers.append(
            Paper(
                source="openalex",
                title=item.get("display_name") or item.get("title") or "Untitled",
                abstract=abstract,
                authors=[(a.get("author") or {}).get("display_name", "") for a in item.get("authorships", []) if (a.get("author") or {}).get("display_name")],
                published_at=parse_iso_date(item.get("publication_date")),
                doi=doi,
                url=item.get("id") or item.get("landing_page_url"),
                pdf_url=best_oa.get("pdf_url"),
                venue=source.get("display_name"),
                citation_count=int(item.get("cited_by_count") or 0),
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
