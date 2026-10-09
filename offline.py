from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from bibliography import row_to_bibtex

ROOT = Path(__file__).resolve().parent
DEFAULT_OFFLINE_DIR = ROOT / "data" / "offline"
DEFAULT_OA_CACHE_DIR = ROOT / "data" / "oa_cache"
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
OA_CACHE_TTL_SECONDS = 30 * 24 * 60 * 60


def _slugify(value: str, max_length: int = 90) -> str:
    value = re.sub(r"[^\w._-]+", "-", value.strip(), flags=re.UNICODE).strip("-.")
    return value[:max_length].rstrip("-.") or "paper"


def _clean_doi(value: str | None) -> str | None:
    if not value:
        return None
    doi = str(value).strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.IGNORECASE)
    doi = doi.strip().strip("/")
    return doi or None


def readable_pdf_filename(row) -> str:
    year = str(row["published_at"] or "undated")[:4]
    authors: list[str] = []
    try:
        authors = json.loads(row["authors_json"] or "[]")
    except (ValueError, TypeError):
        pass
    first_author = "unknown-author"
    if authors:
        author = str(authors[0]).strip()
        # Both "Jane Doe" and "Doe, Jane" are commonly encountered.
        first_author = author.split(",", 1)[0] if "," in author else author.split()[-1]
    return f"{_slugify(year, 12)}_{_slugify(first_author, 32)}_{_slugify(str(row['title']), 72)}.pdf"


def paper_dir(row, base_dir: str | Path = DEFAULT_OFFLINE_DIR) -> Path:
    return Path(base_dir) / f"{row['id']}-{_slugify(row['title'])}"


def offline_pdf_path(row, base_dir: str | Path = DEFAULT_OFFLINE_DIR) -> Path:
    folder = paper_dir(row, base_dir)
    preferred = folder / readable_pdf_filename(row)
    # Backwards compatibility with v0.4.x bundles that used paper.pdf.
    legacy = folder / "paper.pdf"
    if preferred.exists() or not legacy.exists():
        return preferred
    return legacy


def is_available_offline(row, base_dir: str | Path = DEFAULT_OFFLINE_DIR) -> bool:
    return offline_pdf_path(row, base_dir).exists()


def _download_file(url: str, destination: Path) -> int:
    """Download a file atomically and accept it only if it has a PDF signature."""
    request = urllib.request.Request(url, headers={"User-Agent": "LitRadar/0.6.0 (+offline open-access retrieval)"})
    temp_path = destination.with_suffix(destination.suffix + ".part")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
                raise ValueError(f"download exceeds {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB limit")
            first = response.read(5)
            if first != b"%PDF-":
                raise ValueError("response is not a PDF (missing %PDF- signature)")
            total = len(first)
            with temp_path.open("wb") as handle:
                handle.write(first)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise ValueError(f"download exceeds {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB limit")
                    handle.write(chunk)
        os.replace(temp_path, destination)
        return total
    finally:
        temp_path.unlink(missing_ok=True)


def resolve_unpaywall_pdf_urls(
    doi: str | None,
    email: str | None,
    *,
    cache_dir: str | Path = DEFAULT_OA_CACHE_DIR,
    ttl: int = OA_CACHE_TTL_SECONDS,
    timeout: float = 15.0,
) -> list[str]:
    """Return direct PDF URLs from Unpaywall's legal OA locations.

    No request is made without both a DOI and the required contact email.
    Cached results are stored outside source control. The resolver never tries
    to bypass a paywall and ignores landing-page URLs that are not direct PDFs.
    """
    clean_doi = _clean_doi(doi)
    if not clean_doi or not email:
        return []
    digest = hashlib.sha256(clean_doi.casefold().encode("utf-8")).hexdigest()
    cache_path = Path(cache_dir) / f"{digest}.json"
    try:
        if ttl > 0 and cache_path.exists() and (cache_path.stat().st_mtime + ttl) > time.time():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            urls = cached.get("pdf_urls", [])
            return [str(url) for url in urls if isinstance(url, str) and url.startswith("https://")]
    except (OSError, ValueError, TypeError):
        pass

    path = urllib.parse.quote(clean_doi, safe="/")
    url = f"https://api.unpaywall.org/v2/{path}?{urllib.parse.urlencode({'email': email})}"
    request = urllib.request.Request(url, headers={"User-Agent": "LitRadar/0.6.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return []

    urls: list[str] = []
    if payload.get("is_oa"):
        best = payload.get("best_oa_location") or {}
        locations = [best, *(payload.get("oa_locations") or [])]
        for location in locations:
            if not isinstance(location, dict):
                continue
            candidate = location.get("url_for_pdf")
            if isinstance(candidate, str) and candidate.startswith("https://") and candidate not in urls:
                urls.append(candidate)

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps({"doi": clean_doi, "pdf_urls": urls}, indent=2), encoding="utf-8")
    except OSError:
        pass
    return urls


def save_paper_offline(
    row,
    base_dir: str | Path = DEFAULT_OFFLINE_DIR,
    *,
    unpaywall_email: str | None = None,
) -> dict[str, Any]:
    folder = paper_dir(row, base_dir)
    folder.mkdir(parents=True, exist_ok=True)

    metadata = {
        "id": row["id"],
        "title": row["title"],
        "authors": json.loads(row["authors_json"] or "[]"),
        "published_at": row["published_at"],
        "venue": row["venue"],
        "doi": row["doi"],
        "url": row["url"],
        "pdf_url": row["pdf_url"],
        "source": row["source"],
        "relevance_score": row["relevance_score"],
        "status": row["status"],
        "tags": json.loads(row["tags_json"] or "[]"),
        "saved_from_litradar": "0.6.0",
    }
    (folder / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "abstract.txt").write_text(row["abstract"] or "", encoding="utf-8")
    (folder / "citation.bib").write_text(row_to_bibtex(row) + "\n", encoding="utf-8")
    (folder / "notes.txt").write_text(row["notes"] or "", encoding="utf-8")
    if row["llm_assessment_json"]:
        (folder / "llm_assessment.json").write_text(row["llm_assessment_json"], encoding="utf-8")

    pdf_path = offline_pdf_path(row, base_dir)
    downloaded = False
    bytes_downloaded = 0
    errors: list[str] = []
    attempted: list[str] = []
    if not pdf_path.exists():
        # Start each fresh retrieval with a clean status so a recovered PDF
        # URL cannot leave an old failure message behind.
        (folder / "download_error.txt").unlink(missing_ok=True)
        (folder / "retrieval_status.txt").unlink(missing_ok=True)
        direct_candidates = [str(row["pdf_url"])] if row["pdf_url"] else []
        for candidate in direct_candidates:
            attempted.append(candidate)
            try:
                bytes_downloaded = _download_file(candidate, pdf_path)
                downloaded = True
                metadata["downloaded_pdf_url"] = candidate
                metadata["pdf_retrieval"] = "provider"
                (folder / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
                (folder / "download_error.txt").unlink(missing_ok=True)
                (folder / "retrieval_status.txt").unlink(missing_ok=True)
                break
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                errors.append(f"{candidate}: {exc}")
        # Only pay the extra lookup cost when the provider's direct link is
        # absent or unusable. Unpaywall is a legal OA resolver, not paywall bypass.
        if not downloaded and unpaywall_email and row["doi"]:
            for candidate in resolve_unpaywall_pdf_urls(row["doi"], unpaywall_email):
                if candidate in attempted:
                    continue
                attempted.append(candidate)
                try:
                    bytes_downloaded = _download_file(candidate, pdf_path)
                    downloaded = True
                    metadata["downloaded_pdf_url"] = candidate
                    metadata["pdf_retrieval"] = "unpaywall"
                    (folder / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
                    (folder / "download_error.txt").unlink(missing_ok=True)
                    (folder / "retrieval_status.txt").unlink(missing_ok=True)
                    break
                except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                    errors.append(f"{candidate}: {exc}")
        if not downloaded and errors:
            (folder / "download_error.txt").write_text("\n".join(errors), encoding="utf-8")
        elif not downloaded and not attempted:
            (folder / "retrieval_status.txt").write_text(
                "No direct PDF URL was available. Configure UNPAYWALL_EMAIL to try a legal open-access DOI lookup.\n",
                encoding="utf-8",
            )

    return {
        "directory": folder,
        "pdf_path": pdf_path if pdf_path.exists() else None,
        "downloaded": downloaded,
        "bytes": bytes_downloaded,
        "has_pdf": pdf_path.exists(),
        "attempted_urls": attempted,
        "errors": errors,
    }
