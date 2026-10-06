from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
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

    @property
    def title_normalized(self) -> str:
        return " ".join(self.title.casefold().split())


def parse_iso_date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.date().isoformat()
    except ValueError:
        return value[:10] if len(value) >= 10 else value
