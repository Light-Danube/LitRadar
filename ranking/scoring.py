from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np

from sources.base import Paper
from .embeddings import TextEmbedder, cosine_similarity_matrix, cosine_to_unit_interval
from .keywords import KeywordProfile


@dataclass(frozen=True, slots=True)
class Score:
    total: float
    keyword_score: float
    semantic_score: float | None
    group_hits: dict[str, list[str]]
    scoring_version: str = "keyword-v0.1"


def _keyword_score(group_hits: dict[str, list[str]], profile: KeywordProfile) -> float:
    weighted = 0.0
    total_weight = sum(max(group.weight, 0.0) for group in profile.groups)
    if total_weight <= 0:
        return 0.0
    for group in profile.groups:
        hits = group_hits.get(group.name, [])
        if hits:
            coverage = 1.0 + 0.35 * math.log1p(len(hits) - 1)
            weighted += group.weight * coverage
    return min(weighted / total_weight, 1.0)


def paper_text(paper: Paper) -> str:
    return " ".join(
        part for part in [paper.title, paper.abstract, paper.venue or ""] if part
    )


def score_paper(paper: Paper, profile: KeywordProfile) -> Score:
    group_hits = profile.match(paper_text(paper))
    keyword_score = _keyword_score(group_hits, profile)
    return Score(
        total=keyword_score,
        keyword_score=keyword_score,
        semantic_score=None,
        group_hits=group_hits,
        scoring_version="keyword-v0.1",
    )


def score_papers_semantic(
    papers: Sequence[Paper],
    profile: KeywordProfile,
    embedder: TextEmbedder,
) -> list[tuple[Paper, Score]]:
    papers = list(papers)
    if not papers:
        return []
    query_embedding = embedder.encode([profile.as_embedding_text()])[0]
    paper_embeddings = embedder.encode([paper_text(paper) for paper in papers])
    semantic = cosine_to_unit_interval(cosine_similarity_matrix(paper_embeddings, query_embedding))

    ranked: list[tuple[Paper, Score]] = []
    for paper, semantic_score in zip(papers, semantic.tolist()):
        group_hits = profile.match(paper_text(paper))
        keyword_score = _keyword_score(group_hits, profile)
        total = profile.keyword_weight * keyword_score + profile.semantic_weight * float(semantic_score)
        ranked.append(
            (
                paper,
                Score(
                    total=float(total),
                    keyword_score=float(keyword_score),
                    semantic_score=float(semantic_score),
                    group_hits=group_hits,
                    scoring_version=f"semantic-v0.2:{embedder.model_name}",
                ),
            )
        )
    return sorted(ranked, key=_sort_key, reverse=True)


def rank_papers(papers: list[Paper], profile: KeywordProfile) -> list[tuple[Paper, Score]]:
    scored = [(paper, score_paper(paper, profile)) for paper in papers]
    return sorted(scored, key=_sort_key, reverse=True)


def _sort_key(item: tuple[Paper, Score]) -> tuple[float, int, str]:
    paper, score = item
    return (score.total, paper.citation_count, paper.published_at or "")
