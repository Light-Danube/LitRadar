from __future__ import annotations

import urllib.parse
import xml.etree.ElementTree as ET

from .base import Paper, extract_arxiv_id, parse_iso_date
from .http import fetch_bytes

BASE_URL = "https://export.arxiv.org/api/query"
ATOM = "http://www.w3.org/2005/Atom"


def search(
    query: str,
    *,
    max_results: int = 25,
    timeout: float = 20.0,
    retries: int = 3,
    backoff: float = 1.0,
) -> list[Paper]:
    params = urllib.parse.urlencode(
        {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    headers = {"User-Agent": "LitRadar/0.5.3 (academic literature research tool)"}
    xml_text = fetch_bytes(
        f"{BASE_URL}?{params}",
        headers=headers,
        timeout=timeout,
        retries=retries,
        backoff=backoff,
    )

    root = ET.fromstring(xml_text)
    papers: list[Paper] = []
    for entry in root.findall(f"{{{ATOM}}}entry"):
        title = " ".join((entry.findtext(f"{{{ATOM}}}title") or "").split())
        abstract = " ".join((entry.findtext(f"{{{ATOM}}}summary") or "").split())
        authors = [(a.findtext(f"{{{ATOM}}}name") or "").strip() for a in entry.findall(f"{{{ATOM}}}author")]
        entry_id = (entry.findtext(f"{{{ATOM}}}id") or "").strip()
        pdf_url = None
        categories = [c.attrib.get("term", "").strip() for c in entry.findall("{http://arxiv.org/schemas/atom}category")]
        for link in entry.findall(f"{{{ATOM}}}link"):
            if link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href")
                break
        arxiv_id = extract_arxiv_id(entry_id)
        papers.append(
            Paper(
                source="arxiv",
                title=title or "Untitled",
                abstract=abstract,
                authors=[a for a in authors if a],
                published_at=parse_iso_date(entry.findtext(f"{{{ATOM}}}published")),
                updated_at=parse_iso_date(entry.findtext(f"{{{ATOM}}}updated")),
                url=entry_id,
                pdf_url=pdf_url,
                venue="arXiv",
                external_id=entry_id,
                raw={"id": entry_id},
                source_tags=sorted({c for c in categories if c}, key=str.casefold),
                identifiers={"arxiv_id": arxiv_id} if arxiv_id else {},
            )
        )
    return papers
