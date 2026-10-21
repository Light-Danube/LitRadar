from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable
import time

from config import RadarConfig
from .base import Paper
from .cache import load_cached, save_cached
from .http import format_provider_error
from .filters import normalize_metadata_language

SearchFn = Callable[[str, int, RadarConfig], list[Paper]]


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    name: str
    search: SearchFn
    metadata_language_search: Callable[[str, int, RadarConfig, str], list[Paper]] | None = None

    @property
    def capabilities(self) -> tuple[str, ...]:
        return ("free_text", "metadata_language") if self.metadata_language_search else ("free_text",)


class SourceRegistry:
    """Registry for built-in and future source providers."""

    def __init__(self, definitions: list[SourceDefinition] | None = None) -> None:
        self._definitions = {item.name: item for item in (definitions or builtin_definitions())}

    def register(self, definition: SourceDefinition, *, replace: bool = False) -> None:
        if definition.name in self._definitions and not replace:
            raise ValueError(f"Source already registered: {definition.name}")
        self._definitions[definition.name] = definition

    def get(self, name: str) -> SourceDefinition:
        try:
            return self._definitions[name]
        except KeyError as exc:
            raise ValueError(f"Unknown source: {name}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._definitions))

    def enabled(self, configured: tuple[str, ...]) -> tuple[SourceDefinition, ...]:
        return tuple(self.get(name) for name in configured)


def builtin_definitions() -> list[SourceDefinition]:
    from .arxiv import search as arxiv_search
    from .openalex import search as openalex_search
    from .semantic_scholar import search as semantic_scholar_search

    def openalex_adapter(query: str, limit: int, config: RadarConfig) -> list[Paper]:
        return openalex_search(
            query,
            per_page=limit,
            timeout=config.source_timeout,
            retries=config.source_retries,
            backoff=config.source_backoff,
            api_key=config.openalex_api_key,
        )

    def openalex_language_adapter(query: str, limit: int, config: RadarConfig, language: str) -> list[Paper]:
        return openalex_search(query, per_page=limit, timeout=config.source_timeout,
                               retries=config.source_retries, backoff=config.source_backoff,
                               api_key=config.openalex_api_key, metadata_language=language)

    def semantic_scholar_adapter(query: str, limit: int, config: RadarConfig) -> list[Paper]:
        return semantic_scholar_search(
            query,
            limit=limit,
            timeout=config.source_timeout,
            retries=config.source_retries,
            backoff=config.source_backoff,
            api_key=config.semantic_scholar_api_key,
        )

    def arxiv_adapter(query: str, limit: int, config: RadarConfig) -> list[Paper]:
        return arxiv_search(
            query,
            max_results=limit,
            timeout=config.source_timeout,
            retries=config.source_retries,
            backoff=config.source_backoff,
        )

    return [
        SourceDefinition("openalex", openalex_adapter, openalex_language_adapter),
        SourceDefinition("semantic_scholar", semantic_scholar_adapter),
        SourceDefinition("arxiv", arxiv_adapter),
    ]


def default_registry() -> SourceRegistry:
    return SourceRegistry()


def validate_metadata_language_sources(sources, language, registry=None) -> str:
    language = normalize_metadata_language(language)
    if language != "any":
        definitions = (registry or default_registry()).enabled(tuple(sources))
        unsupported = [d.name for d in definitions if d.metadata_language_search is None]
        if unsupported:
            raise ValueError("Metadata-language filter unsupported for: " + ", ".join(unsupported)
                             + ". Select OpenAlex explicitly or choose any (unfiltered).")
    return language


def search_all_sources(
    query: str,
    *,
    sources: list[str] | tuple[str, ...] | None = None,
    per_source: int = 20,
    config: RadarConfig | None = None,
    registry: SourceRegistry | None = None,
    progress: Callable[[str, str, str], None] | None = None,
    metadata_language: str = "any",
) -> tuple[dict[str, list[Paper]], dict[str, Exception]]:
    """Search providers concurrently with per-source cache/retries and progress events.

    ``progress(event, source, message)`` is invoked from the calling thread for
    cache/start/completion events. A callback failure is ignored deliberately so
    that UI/logging code cannot make a source search fail.
    """
    def emit(event: str, source: str, message: str) -> None:
        if progress is not None:
            try:
                progress(event, source, message)
            except Exception:
                pass
    config = config or RadarConfig.load()
    registry = registry or default_registry()
    requested = tuple(sources or config.enabled_sources)
    definitions = registry.enabled(requested)
    metadata_language = validate_metadata_language_sources(requested, metadata_language, registry)
    filter_options = {"metadata_language": metadata_language} if metadata_language != "any" else {}

    results: dict[str, list[Paper]] = {}
    errors: dict[str, Exception] = {}
    missing: list[SourceDefinition] = []

    for definition in definitions:
        cached = load_cached(definition.name, query, per_source, config.source_cache_ttl, **filter_options)
        if cached is not None:
            results[definition.name] = cached
            emit("cache-hit", definition.name, f"cache hit ({len(cached)} papers)")
        else:
            missing.append(definition)
            emit("started", definition.name, "request started")

    if not missing:
        return results, errors

    workers = min(max(config.source_workers, 1), len(missing))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="litradar-source") as executor:
        future_map = {
            (executor.submit(definition.metadata_language_search, query, per_source, config, metadata_language)
             if filter_options else executor.submit(definition.search, query, per_source, config)): definition
            for definition in missing
        }
        for future in as_completed(future_map):
            definition = future_map[future]
            try:
                papers = future.result()
                results[definition.name] = papers
                save_cached(definition.name, query, per_source, papers, **filter_options)
                emit("completed", definition.name, f"received {len(papers)} papers")
            except Exception as exc:
                errors[definition.name] = exc
                emit("error", definition.name, format_provider_error(exc))

    return results, errors
