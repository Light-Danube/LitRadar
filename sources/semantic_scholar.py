from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from .base import Paper, parse_iso_date

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def search(query: str, *, limit: int = 25) -> list[Paper]:
    fields = "title,abstract,authors,year,venue,url,externalIds,citationCount,publicationDate,openAccessPdf"
    params = urllib.parse.urlencode({"query": query, "limit": limit, "fields": fields})
    request = urllib.request.Request(f"{BASE_URL}?{params}", headers={"User-Agent": "LitRadar/0.3"})
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        request.add_header("x-api-key", api_key)
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)

    papers: list[Paper] = []
    for item in payload.get("data", []):
        external_ids = item.get("externalIds") or {}
        doi = external_ids.get("DOI")
        open_access_pdf = item.get("openAccessPdf") or {}
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
                external_id=item.get("paperId"),
                raw=item,
            )
        )
    return papers
