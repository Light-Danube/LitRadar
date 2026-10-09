from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from config import RadarConfig
from ranking.keywords import KeywordProfile
from ranking.scoring import Score, rank_papers, score_papers_semantic
from sources.base import Paper
from sources.registry import search_all_sources
from storage.sqlite import PaperStore


@dataclass(frozen=True, slots=True)
class SearchSummary:
    query: str
    fetched: int
    newly_stored: int
    library_total: int
    source_results: dict[str, int]
    source_errors: dict[str, str]
    scoring_version: str


def _rank(
    papers: list[Paper],
    profile: KeywordProfile,
    semantic: bool,
    progress: Callable[[str, str, str], None] | None = None,
) -> list[tuple[Paper, Score]]:
    if semantic:
        try:
            from ranking.embeddings import SentenceTransformerEmbedder
            embedder = SentenceTransformerEmbedder(profile.embedding_model)
            return score_papers_semantic(papers, profile, embedder)
        except Exception as exc:
            # Semantic scoring is an enhancement, not a reason to lose a search.
            if progress is not None:
                try:
                    progress("warning", "ranking", f"semantic scoring unavailable; using keywords ({exc})")
                except Exception:
                    pass
    return rank_papers(papers, profile)


def search_and_ingest(
    query: str,
    *,
    db_path: str | Path,
    profile_path: str | Path,
    semantic: bool = True,
    sources: tuple[str, ...] | list[str] | None = None,
    per_source: int = 20,
    config: RadarConfig | None = None,
    progress: Callable[[str, str, str], None] | None = None,
) -> tuple[SearchSummary, list[tuple[Paper, Score]]]:
    """Search configured providers and persist their ranked results.

    This service is shared by the CLI and TUI. It opens its own SQLite
    connection, which is important when called from a Textual worker thread.
    """
    config = config or RadarConfig.load()
    profile = KeywordProfile.from_json(profile_path)
    requested_sources = tuple(sources) if sources else config.enabled_sources
    store = PaperStore(db_path)
    try:
        before = store.total_count()
        source_results, source_errors = search_all_sources(
            query,
            sources=requested_sources,
            per_source=per_source,
            config=config,
            progress=progress,
        )
        papers: list[Paper] = []
        counts: dict[str, int] = {}
        for source in requested_sources:
            fetched = source_results.get(source, [])
            counts[source] = len(fetched)
            papers.extend(fetched)
        ranked = _rank(papers, profile, semantic=semantic, progress=progress)
        store.upsert_papers(
            (
                paper,
                score.total,
                score.group_hits,
                score.keyword_score,
                score.semantic_score,
                score.scoring_version,
            )
            for paper, score in ranked
        )
        after = store.total_count()
        summary = SearchSummary(
            query=query,
            fetched=len(papers),
            newly_stored=max(after - before, 0),
            library_total=after,
            source_results=counts,
            source_errors={name: str(error) for name, error in source_errors.items()},
            scoring_version=ranked[0][1].scoring_version if ranked else ("keyword-v0.1" if not semantic else "semantic-or-keyword"),
        )
        return summary, ranked
    finally:
        store.close()
