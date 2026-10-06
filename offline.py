from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from bibliography import row_to_bibtex

ROOT = Path(__file__).resolve().parent
DEFAULT_OFFLINE_DIR = ROOT / "data" / "offline"
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024


def _slugify(value: str, max_length: int = 90) -> str:
    value = re.sub(r"[^\w._-]+", "-", value.strip(), flags=re.UNICODE).strip("-.")
    return value[:max_length].rstrip("-.") or "paper"


def paper_dir(row, base_dir: str | Path = DEFAULT_OFFLINE_DIR) -> Path:
    return Path(base_dir) / f"{row['id']}-{_slugify(row['title'])}"


def offline_pdf_path(row, base_dir: str | Path = DEFAULT_OFFLINE_DIR) -> Path:
    return paper_dir(row, base_dir) / "paper.pdf"


def is_available_offline(row, base_dir: str | Path = DEFAULT_OFFLINE_DIR) -> bool:
    return offline_pdf_path(row, base_dir).exists()


def _download_file(url: str, destination: Path) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": "LitRadar/0.4.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_DOWNLOAD_BYTES:
            raise ValueError(f"download exceeds {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB limit")
        destination.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        with destination.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    handle.close()
                    destination.unlink(missing_ok=True)
                    raise ValueError(f"download exceeds {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB limit")
                handle.write(chunk)
    return total


def save_paper_offline(row, base_dir: str | Path = DEFAULT_OFFLINE_DIR) -> dict[str, Any]:
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
        "saved_from_litradar": "0.4.1",
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
    if not pdf_path.exists() and row["pdf_url"]:
        try:
            bytes_downloaded = _download_file(row["pdf_url"], pdf_path)
            downloaded = True
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            (folder / "download_error.txt").write_text(str(exc), encoding="utf-8")

    return {
        "directory": folder,
        "pdf_path": pdf_path if pdf_path.exists() else None,
        "downloaded": downloaded,
        "bytes": bytes_downloaded,
        "has_pdf": pdf_path.exists(),
    }
