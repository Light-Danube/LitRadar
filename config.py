from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional import fallback
    load_dotenv = None

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
DEFAULT_SOURCES = ("openalex", "semantic_scholar", "arxiv")


def _load_dotenv() -> None:
    """Load local .env once, without overriding explicitly exported variables."""
    if load_dotenv is not None:
        load_dotenv(dotenv_path=ENV_PATH, override=False)


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "on", "y"}


def _get_int(name: str, default: int, minimum: int = 0) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return max(int(value), minimum)
    except ValueError:
        return default


def _get_float(name: str, default: float, minimum: float = 0.0) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return max(float(value), minimum)
    except ValueError:
        return default


def _split_sources(value: str | None) -> tuple[str, ...]:
    if not value:
        return DEFAULT_SOURCES
    values = tuple(dict.fromkeys(part.strip().casefold() for part in value.split(",") if part.strip()))
    return values or DEFAULT_SOURCES


@dataclass(frozen=True, slots=True)
class RadarConfig:
    """Runtime configuration loaded from environment and optional .env file."""

    enabled_sources: tuple[str, ...] = field(default_factory=lambda: DEFAULT_SOURCES)
    source_workers: int = 3
    source_timeout: float = 20.0
    source_retries: int = 3
    source_backoff: float = 2.0
    source_cache_ttl: int = 3600

    openalex_api_key: str | None = None
    semantic_scholar_api_key: str | None = None
    openalex_mailto: str | None = None
    unpaywall_email: str | None = None

    personalized_weight: float = 0.20
    personalization_min_feedback: int = 5
    personalization_scan_limit: int = 5000
    personalization_enabled: bool = True

    llm_provider: str = "none"
    llm_model: str = ""

    @classmethod
    def load(cls) -> "RadarConfig":
        _load_dotenv()
        return cls(
            enabled_sources=_split_sources(os.getenv("LITRADAR_SOURCES")),
            source_workers=_get_int("LITRADAR_SOURCE_WORKERS", 3, 1),
            source_timeout=_get_float("LITRADAR_SOURCE_TIMEOUT", 20.0, 1.0),
            source_retries=_get_int("LITRADAR_SOURCE_RETRIES", 3, 0),
            source_backoff=_get_float("LITRADAR_SOURCE_BACKOFF", 2.0, 0.0),
            source_cache_ttl=_get_int("LITRADAR_SOURCE_CACHE_TTL", 3600, 0),
            openalex_api_key=os.getenv("OPENALEX_API_KEY") or None,
            semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY") or None,
            openalex_mailto=os.getenv("LITRADAR_MAILTO") or None,
            unpaywall_email=os.getenv("UNPAYWALL_EMAIL") or None,
            personalized_weight=min(_get_float("LITRADAR_PERSONALIZATION_WEIGHT", 0.20, 0.0), 1.0),
            personalization_min_feedback=_get_int("LITRADAR_PERSONALIZATION_MIN_FEEDBACK", 5, 0),
            personalization_scan_limit=_get_int("LITRADAR_PERSONALIZATION_SCAN_LIMIT", 5000, 100),
            personalization_enabled=_get_bool("LITRADAR_PERSONALIZATION_ENABLED", True),
            llm_provider=os.getenv("LITRADAR_LLM_PROVIDER", "none").strip().casefold() or "none",
            llm_model=os.getenv("LITRADAR_LLM_MODEL", "").strip(),
        )

    def masked_dict(self) -> dict[str, object]:
        """Return user-facing configuration without exposing secrets."""
        return {
            "enabled_sources": list(self.enabled_sources),
            "source_workers": self.source_workers,
            "source_timeout": self.source_timeout,
            "source_retries": self.source_retries,
            "source_backoff": self.source_backoff,
            "source_cache_ttl": self.source_cache_ttl,
            "openalex_api_key": bool(self.openalex_api_key),
            "semantic_scholar_api_key": bool(self.semantic_scholar_api_key),
            "openalex_mailto_legacy": bool(self.openalex_mailto),
            "unpaywall_email_configured": bool(self.unpaywall_email),
            "personalized_weight": self.personalized_weight,
            "personalization_min_feedback": self.personalization_min_feedback,
            "personalization_scan_limit": self.personalization_scan_limit,
            "personalization_enabled": self.personalization_enabled,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
        }
