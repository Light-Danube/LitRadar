from __future__ import annotations

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .base import Paper, parse_iso_date

BASE_URL = "https://export.arxiv.org/api/query"
ATOM = "http://www.w3.org/2005/Atom"


def search(query: str, *, max_results: int = 25) -> list[Paper]:
    params = urllib.parse.urlencode(
        {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
    )
    request = urllib.request.Request(f"{BASE_URL}?{params}", headers={"User-Agent": "LitRadar/0.3"})
    with urllib.request.urlopen(request, timeout=20) as response:
        xml_text = response.read()

    root = ET.fromstring(xml_text)
    papers: list[Paper] = []
    for entry in root.findall(f"{{{ATOM}}}entry"):
        title = " ".join((entry.findtext(f"{{{ATOM}}}title") or "").split())
        abstract = " ".join((entry.findtext(f"{{{ATOM}}}summary") or "").split())
        authors = [
            (author.findtext(f"{{{ATOM}}}name") or "").strip()
            for author in entry.findall(f"{{{ATOM}}}author")
        ]
        entry_id = (entry.findtext(f"{{{ATOM}}}id") or "").strip()
        url = entry_id
        pdf_url = None
        for link in entry.findall(f"{{{ATOM}}}link"):
            if link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href")
                break
        papers.append(
            Paper(
                source="arxiv",
                title=title or "Untitled",
                abstract=abstract,
                authors=[a for a in authors if a],
                published_at=parse_iso_date(entry.findtext(f"{{{ATOM}}}published")),
                updated_at=parse_iso_date(entry.findtext(f"{{{ATOM}}}updated")),
                url=url,
                pdf_url=pdf_url,
                external_id=entry_id,
                raw={"id": entry_id},
            )
        )
    return papers
