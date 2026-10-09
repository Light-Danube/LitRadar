from __future__ import annotations

import json
import urllib.parse

from .base import Paper, parse_iso_date
from .http import fetch_bytes

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def search(
    query: str,
    *,
    limit: int = 25,
    timeout: float = 20.0,
    retries: int = 3,
    backoff: float = 1.0,
    api_key: str | None = None,
) -> list[Paper]:
    fields = "title,abstract,authors,year,venue,url,externalIds,citationCount,referenceCount,influentialCitationCount,publicationDate,openAccessPdf,fieldsOfStudy"
    params = urllib.parse.urlencode({"query": query, "limit": limit, "fields": fields})
    headers = {"User-Agent": "LitRadar/0.5.4"}
    if api_key:
        headers["x-api-key"] = api_key
    payload = json.loads(fetch_bytes(f"{BASE_URL}?{params}", headers=headers, timeout=timeout, retries=retries, backoff=backoff))

    papers: list[Paper] = []
    for item in payload.get("data", []):
        external_ids = item.get("externalIds") or {}
        doi = external_ids.get("DOI")
        open_access_pdf = item.get("openAccessPdf") or {}
        source_tags = [str(value).strip() for value in (item.get("fieldsOfStudy") or []) if str(value).strip()]
        identifiers = {"semantic_scholar_id": str(item.get("paperId"))} if item.get("paperId") else {}
        if external_ids.get("ArXiv"):
            identifiers["arxiv_id"] = str(external_ids["ArXiv"])
        papers.append(
            Paper(
                source="semantic_scholar",
                title=item.get("title") or "Untitled",
                abstract=item.get("abstract") or "",
                authors=[a.get("name", "") for a in item.get("authors", []) if a.get("name")],
                published_at=parse_iso_date(item.get("publicationDate")),
                doi=doi,
                url=item.get("url"),
                pdf_url=open_access_pdf.get("url"),
                venue=item.get("venue"),
                citation_count=int(item.get("citationCount") or 0),
                reference_count=int(item.get("referenceCount") or 0),
                influential_citation_count=(
                    int(item["influentialCitationCount"])
                    if item.get("influentialCitationCount") is not None else None
                ),
                external_id=item.get("paperId"),
                raw=item,
                source_tags=sorted(set(source_tags), key=str.casefold),
                identifiers=identifiers,
            )
        )
    return papers
