from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Iterable, Mapping

from .keywords import KeywordProfile

# Explicitly distinguish "I like this" from "I don't want this".
STATUS_WEIGHTS = {
    "to-read": 0.8,
    "read": 1.2,
    "archived": 0.25,
    "new": 0.0,
    "dismissed": -1.0,
}
DISMISS_REASON_WEIGHTS = {
    "irrelevant": -1.0,
    "too broad": -0.65,
    "wrong domain": -0.8,
    "already known": -0.35,
    "duplicate": 0.0,
    "other": -0.4,
    "user": -0.75,
}


@dataclass(frozen=True, slots=True)
class PersonalizationModel:
    interactions: int
    group_signal: Mapping[str, float]

    @property
    def ready(self) -> bool:
        return bool(self.group_signal)


@dataclass(frozen=True, slots=True)
class PersonalizationResult:
    score: float
    signal: float
    boost: float


def build_model(rows: Iterable, *, min_feedback: int = 5) -> PersonalizationModel:
    group_values: dict[str, float] = {}
    group_abs: dict[str, float] = {}
    interactions = 0

    for row in rows:
        weight = _row_feedback_weight(row)
        if weight == 0:
            continue
        interactions += 1
        try:
            matched = json.loads(row["matched_groups_json"] or "{}")
        except (json.JSONDecodeError, TypeError):
            matched = {}
        for group_name in matched:
            group_values[group_name] = group_values.get(group_name, 0.0) + weight
            group_abs[group_name] = group_abs.get(group_name, 0.0) + abs(weight)

    if interactions < min_feedback:
        return PersonalizationModel(interactions=interactions, group_signal={})

    signals = {
        group: math.tanh(value / max(1.0, group_abs[group] * 0.6 + 1.0))
        for group, value in group_values.items()
    }
    return PersonalizationModel(interactions=interactions, group_signal=signals)


def score_rows(rows: Iterable, model: PersonalizationModel, profile: KeywordProfile, weight: float = 0.20) -> list[tuple[object, PersonalizationResult]]:
    rows = list(rows)
    results: list[tuple[object, PersonalizationResult]] = []
    group_weights = {group.name: max(group.weight, 0.0) for group in profile.groups}
    for row in rows:
        base = float(row["relevance_score"] or 0.0)
        signal = _candidate_signal(row, model, group_weights)
        boost = weight * signal * (1.0 - base) if signal else 0.0
        personal = min(max(base + boost, 0.0), 1.0)
        results.append((row, PersonalizationResult(score=personal, signal=signal, boost=boost)))
    results.sort(key=lambda item: (item[1].score, float(item[0]["citation_count"] or 0), item[0]["published_at"] or "", -int(item[0]["id"])), reverse=True)
    return results


def neutral_results(rows: Iterable) -> list[tuple[object, PersonalizationResult]]:
    """Return base scores unchanged when personalization is disabled."""
    return [
        (row, PersonalizationResult(score=float(row["relevance_score"] or 0.0), signal=0.0, boost=0.0))
        for row in rows
    ]


def _candidate_signal(row, model: PersonalizationModel, group_weights: Mapping[str, float]) -> float:
    if not model.group_signal:
        return 0.0
    try:
        matched = json.loads(row["matched_groups_json"] or "{}")
    except (json.JSONDecodeError, TypeError):
        matched = {}
    names = [name for name in matched if name in model.group_signal]
    if not names:
        return 0.0
    total_weight = sum(group_weights.get(name, 1.0) for name in names)
    if total_weight <= 0:
        return 0.0
    return max(-1.0, min(1.0, sum(model.group_signal[name] * group_weights.get(name, 1.0) for name in names) / total_weight))


def _row_feedback_weight(row) -> float:
    status = str(row["status"] or "new")
    implicit = 0.0
    if status == "dismissed":
        reason = str(row["dismiss_reason"] or "user").casefold()
        implicit = DISMISS_REASON_WEIGHTS.get(reason, STATUS_WEIGHTS[status])
    else:
        implicit = STATUS_WEIGHTS.get(status, 0.0)
    try:
        explicit = float(row["explicit_feedback"] or 0.0)
    except (KeyError, TypeError, ValueError):
        explicit = 0.0
    # Explicit signals are stronger than workflow-derived hints, but remain bounded.
    return max(-1.5, min(1.5, implicit * 0.5 + explicit))
