from __future__ import annotations

import json
from pathlib import Path

from ranking.keywords import KeywordProfile
from ranking.personalization import build_model, score_rows


def profile(tmp_path: Path) -> KeywordProfile:
    path = tmp_path / "profile.json"
    path.write_text(
        json.dumps(
            {
                "name": "test",
                "description": "emotion and sarcasm",
                "ranking": {"keyword_weight": 0.5, "semantic_weight": 0.5},
                "groups": [
                    {"name": "emotion", "weight": 4, "terms": ["emotion"]},
                    {"name": "sarcasm", "weight": 4, "terms": ["sarcasm"]},
                ],
            }
        ),
        encoding="utf-8",
    )
    return KeywordProfile.from_json(path)


def row(status: str, groups: dict[str, list[str]], reason: str | None = None, explicit: float = 0.0):
    return {
        "status": status,
        "dismiss_reason": reason,
        "matched_groups_json": json.dumps(groups),
        "explicit_feedback": explicit,
    }


def candidate(paper_id: int, base: float, groups: dict[str, list[str]]):
    return {
        "id": paper_id,
        "relevance_score": base,
        "citation_count": 0,
        "published_at": "2026-01-01",
        "matched_groups_json": json.dumps(groups),
    }


def test_personalization_is_neutral_before_min_feedback(tmp_path):
    p = profile(tmp_path)
    model = build_model([row("read", {"emotion": ["emotion"]})], min_feedback=5)
    results = score_rows([candidate(1, 0.5, {"emotion": ["emotion"]})], model, p, weight=0.2)
    assert results[0][1].score == 0.5
    assert model.ready is False


def test_positive_feedback_boosts_matching_group(tmp_path):
    p = profile(tmp_path)
    feedback = [row("read", {"emotion": ["emotion"]}, explicit=1.0) for _ in range(5)]
    model = build_model(feedback, min_feedback=5)
    emotion = candidate(1, 0.6, {"emotion": ["emotion"]})
    sarcasm = candidate(2, 0.6, {"sarcasm": ["sarcasm"]})
    ranked = score_rows([emotion, sarcasm], model, p, weight=0.2)
    by_id = {r["id"]: result for r, result in ranked}
    assert by_id[1].score > 0.6
    assert by_id[2].score == 0.6


def test_negative_feedback_lowers_matching_group_and_duplicate_dismiss_is_neutral(tmp_path):
    p = profile(tmp_path)
    feedback = [row("dismissed", {"emotion": ["emotion"]}, reason="irrelevant") for _ in range(5)]
    feedback += [row("dismissed", {"sarcasm": ["sarcasm"]}, reason="duplicate") for _ in range(10)]
    model = build_model(feedback, min_feedback=5)
    results = score_rows(
        [candidate(1, 0.7, {"emotion": ["emotion"]}), candidate(2, 0.7, {"sarcasm": ["sarcasm"]})],
        model,
        p,
        weight=0.2,
    )
    by_id = {r["id"]: result for r, result in results}
    assert by_id[1].score < 0.7
    assert by_id[2].score == 0.7


def test_personalized_explanation_names_matched_preference_group(tmp_path):
    from ranking.personalization import PersonalizationModel, explain_candidate

    p = profile(tmp_path)
    model = PersonalizationModel(interactions=8, group_signal={"emotion": 0.75, "sarcasm": -0.40})
    paper = candidate(10, 0.65, {"emotion": ["emotion recognition"]})
    explanation = explain_candidate(paper, model, p, weight=0.2)
    assert "boosted by preferences" in explanation
    assert "emotion" in explanation
    assert "weight=0.20" in explanation
