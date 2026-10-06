from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol

from sources.base import Paper
from ranking.keywords import KeywordProfile
from ranking.scoring import Score


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(self, prompt: str) -> str:
        ...


@dataclass(frozen=True, slots=True)
class Assessment:
    relevance: float
    potential_overlap: float
    overlap_level: str
    summary: str
    fit_reason: str
    overlap_reason: str
    suggested_tags: list[str]
    provider: str
    model: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "relevance": self.relevance,
            "potential_overlap": self.potential_overlap,
            "overlap_level": self.overlap_level,
            "summary": self.summary,
            "fit_reason": self.fit_reason,
            "overlap_reason": self.overlap_reason,
            "suggested_tags": self.suggested_tags,
            "provider": self.provider,
            "model": self.model,
        }


def build_prompt(paper: Paper, score: Score, profile: KeywordProfile) -> str:
    return f"""You are a research literature triage assistant.
Evaluate a paper against the research profile below.

IMPORTANT:
- Do not claim that a paper establishes or disproves novelty.
- Estimate only topical relevance and potential overlap with the research direction.
- Base the assessment on the title, abstract, and metadata provided.
- Return ONLY valid JSON with the schema shown below.

RESEARCH PROFILE:
{profile.description}

PROFILE GROUPS:
{profile.as_embedding_text()}

PAPER TITLE:
{paper.title}

ABSTRACT:
{paper.abstract}

VENUE:
{paper.venue or 'Unknown'}

KEYWORD SCORE: {score.keyword_score:.4f}
SEMANTIC SCORE: {score.semantic_score if score.semantic_score is not None else 'n/a'}
MATCHED GROUPS: {json.dumps(score.group_hits, ensure_ascii=False)}

JSON SCHEMA:
{{
  "relevance": 0.0,
  "potential_overlap": 0.0,
  "overlap_level": "low|medium|high",
  "summary": "brief summary",
  "fit_reason": "why this is relevant or not",
  "overlap_reason": "why it may overlap with the research direction",
  "suggested_tags": ["tag1", "tag2"]
}}
"""


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("LLM response did not contain a JSON object") from exc
        value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("LLM response must be a JSON object")
    return value


def coerce_assessment(payload: dict[str, Any], *, provider: str, model: str) -> Assessment:
    relevance = _clamp_float(payload.get("relevance", 0.0))
    overlap = _clamp_float(payload.get("potential_overlap", 0.0))
    level = str(payload.get("overlap_level", "low")).lower()
    if level not in {"low", "medium", "high"}:
        level = "low"
    tags = payload.get("suggested_tags", [])
    if not isinstance(tags, list):
        tags = [str(tags)]
    return Assessment(
        relevance=relevance,
        potential_overlap=overlap,
        overlap_level=level,
        summary=str(payload.get("summary", "")),
        fit_reason=str(payload.get("fit_reason", "")),
        overlap_reason=str(payload.get("overlap_reason", "")),
        suggested_tags=[str(x) for x in tags[:12]],
        provider=provider,
        model=model,
    )


def assess_paper(provider: LLMProvider, paper: Paper, score: Score, profile: KeywordProfile) -> Assessment:
    raw = provider.complete(build_prompt(paper, score, profile))
    return coerce_assessment(parse_json_response(raw), provider=provider.name, model=provider.model)


def _clamp_float(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
