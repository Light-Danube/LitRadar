from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable

from config import RadarConfig
from ranking.keywords import KeywordProfile
from ranking.scoring import Score, rank_papers, score_papers_semantic
from sources.base import Paper
from sources.http import format_provider_error
from sources.registry import search_all_sources, validate_metadata_language_sources
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
    metadata_language: str = "any"


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
        except Exception:
            # Semantic scoring is an enhancement, not a reason to lose a search.
            if progress is not None:
                try:
                    progress("warning", "ranking", "semantic scoring unavailable; using keywords")
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
    metadata_language: str = "any",
) -> tuple[SearchSummary, list[tuple[Paper, Score]]]:
    """Search configured providers and persist their ranked results.

    This service is shared by the CLI and TUI. It opens its own SQLite
    connection, which is important when called from a Textual worker thread.
    """
    config = config or RadarConfig.load()
    profile = KeywordProfile.from_json(profile_path)
    requested_sources = tuple(sources) if sources else config.enabled_sources
    metadata_language = validate_metadata_language_sources(requested_sources, metadata_language)
    filter_options = {"metadata_language": metadata_language} if metadata_language != "any" else {}
    store = PaperStore(db_path)
    try:
        before = store.total_count()
        if progress is not None:
            progress("phase", "search", f"Searching {len(requested_sources)} online source(s).")
        source_results, source_errors = search_all_sources(
            query,
            sources=requested_sources,
            per_source=per_source,
            config=config,
            progress=progress,
            **filter_options,
        )
        papers: list[Paper] = []
        counts: dict[str, int] = {}
        for source in requested_sources:
            fetched = source_results.get(source, [])
            counts[source] = len(fetched)
            papers.extend(fetched)
        if progress is not None:
            progress("phase", "ranking", f"Ranking {len(papers)} fetched paper(s); this can take longer when semantic scoring is enabled.")
        ranked = _rank(papers, profile, semantic=semantic, progress=progress)
        if not semantic and ranked:
            # Scheduled/background scans default to lightweight keyword scoring.
            # Do not let a later keyword-only refresh erase a previously computed
            # semantic score for an already-known work.
            preserved: list[tuple[Paper, Score]] = []
            for paper, score in ranked:
                existing_id = store.find_existing_paper_id(paper)
                existing = store.get(existing_id) if existing_id is not None else None
                if existing is not None and existing["semantic_score"] is not None and str(existing["scoring_version"]).startswith("semantic-v0.2"):
                    try:
                        existing_groups = json.loads(existing["matched_groups_json"] or "{}")
                    except (ValueError, TypeError):
                        existing_groups = {}
                    score = Score(
                        total=float(existing["relevance_score"] or 0.0),
                        keyword_score=float(existing["keyword_score"] or 0.0),
                        semantic_score=float(existing["semantic_score"]),
                        group_hits=existing_groups,
                        scoring_version=str(existing["scoring_version"]),
                    )
                preserved.append((paper, score))
            ranked = preserved
        if progress is not None:
            progress("phase", "saving", f"Saving {len(ranked)} ranked paper(s) to the local library.")
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
            source_errors={name: format_provider_error(error) for name, error in source_errors.items()},
            scoring_version=ranked[0][1].scoring_version if ranked else ("keyword-v0.1" if not semantic else "semantic-or-keyword"),
            metadata_language=metadata_language,
        )
        if progress is not None:
            progress(
                "phase",
                "complete",
                f"Search complete: fetched {summary.fetched}; added {summary.newly_stored}; library total {summary.library_total}.",
            )
        return summary, ranked
    finally:
        store.close()
