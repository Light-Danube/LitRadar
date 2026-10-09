from __future__ import annotations

import json
import threading
import time
import urllib.parse

from .base import Paper, parse_iso_date
from .http import fetch_bytes

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
_RATE_LOCK = threading.Lock()
_LAST_REQUEST_AT = 0.0


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
    params = urllib.parse.urlencode({"query": query, "limit": min(max(int(limit), 1), 100), "fields": fields})
    payload = _get_json(f"{BASE_URL}?{params}", api_key=api_key, timeout=timeout, retries=retries, backoff=backoff)
    return [_paper_from_record(item) for item in payload.get("data", []) if isinstance(item, dict)]


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
    """Fetch a bounded page of references or citing papers from Semantic Scholar."""
    if direction not in {"references", "cited-by"}:
        raise ValueError(f"Unsupported Semantic Scholar citation direction: {direction}")
    endpoint = "references" if direction == "references" else "citations"
    fields = "title,year,venue,url,externalIds,authors,publicationDate,citationCount,referenceCount"
    params = urllib.parse.urlencode({"offset": 0, "limit": min(max(int(limit), 1), 100), "fields": fields})
    encoded_id = urllib.parse.quote(str(identifier).strip(), safe="")
    url = f"https://api.semanticscholar.org/graph/v1/paper/{encoded_id}/{endpoint}?{params}"
    payload = _get_json(url, api_key=api_key, timeout=timeout, retries=retries, backoff=backoff)
    nested_key = "citedPaper" if direction == "references" else "citingPaper"
    papers = []
    for item in payload.get("data", []):
        record = item.get(nested_key) if isinstance(item, dict) else None
        if isinstance(record, dict) and (record.get("paperId") or record.get("title")):
            papers.append(_paper_from_record(record))
    return papers


def _get_json(url: str, *, api_key: str | None, timeout: float, retries: int, backoff: float) -> dict:
    # Stay below the commonly enforced unauthenticated Semantic Scholar rate
    # limit. A single process-wide lock avoids bursts from concurrent searches.
    global _LAST_REQUEST_AT
    minimum_interval = 1.05 if not api_key else 0.25
    with _RATE_LOCK:
        now = time.monotonic()
        delay = minimum_interval - (now - _LAST_REQUEST_AT)
        if delay > 0:
            time.sleep(delay)
        _LAST_REQUEST_AT = time.monotonic()
    headers = {"User-Agent": "LitRadar/0.6 (citation intelligence)"}
    if api_key:
        headers["x-api-key"] = api_key
    return json.loads(fetch_bytes(url, headers=headers, timeout=timeout, retries=retries, backoff=backoff))


def _paper_from_record(item: dict) -> Paper:
    external_ids = item.get("externalIds") or {}
    doi = external_ids.get("DOI")
    open_access_pdf = item.get("openAccessPdf") or {}
    source_tags = [str(value).strip() for value in (item.get("fieldsOfStudy") or []) if str(value).strip()]
    identifiers = {"semantic_scholar_id": str(item.get("paperId"))} if item.get("paperId") else {}
    if external_ids.get("ArXiv"):
        identifiers["arxiv_id"] = str(external_ids["ArXiv"])
    for external_key, identifier_type in (("PubMed", "pmid"), ("PubMedCentral", "pmcid"), ("CorpusId", "corpus_id")):
        if external_ids.get(external_key):
            identifiers[identifier_type] = str(external_ids[external_key])
    if external_ids.get("OpenAlex"):
        identifiers["openalex_id"] = str(external_ids["OpenAlex"])
    return Paper(
        source="semantic_scholar",
        title=item.get("title") or "Untitled",
        abstract=item.get("abstract") or "",
        authors=[a.get("name", "") for a in item.get("authors", []) if a.get("name")],
        published_at=parse_iso_date(item.get("publicationDate")) or (str(item["year"]) if item.get("year") else None),
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
