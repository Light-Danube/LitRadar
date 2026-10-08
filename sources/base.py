from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any


@dataclass(slots=True)
class Paper:
    source: str
    title: str
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    published_at: str | None = None
    updated_at: str | None = None
    doi: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    venue: str | None = None
    citation_count: int = 0
    external_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    source_tags: list[str] = field(default_factory=list)
    identifiers: dict[str, str] = field(default_factory=dict)

    @property
    def title_normalized(self) -> str:
        return normalize_title(self.title)

    @property
    def title_hash(self) -> str:
        import hashlib
        return hashlib.sha256(self.title_normalized.encode("utf-8")).hexdigest()


def parse_iso_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.date().isoformat()
    except ValueError:
        return value[:10] if len(value) >= 10 else value


def normalize_title(title: str) -> str:
    """Normalize a paper title for conservative cross-source deduplication."""
    import re
    import unicodedata

    text = unicodedata.normalize("NFKC", title or "").casefold()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def extract_arxiv_id(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip().rstrip("/")
    text = re.sub(r"^https?://(?:export\.)?arxiv.org/(?:abs|pdf)/", "", text, flags=re.IGNORECASE)
    if text.lower().endswith(".pdf"):
        text = text[:-4]
    # arXiv ids can be old style (hep-th/...) or new numeric ids.
    return text or None
