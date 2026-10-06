from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from llm.assessment import assess_paper, parse_json_response
from ranking.keywords import KeywordProfile
from ranking.scoring import Score
from sources.base import Paper


class FakeProvider:
    name = "fake"
    model = "test-model"

    def complete(self, prompt: str) -> str:
        assert "RESEARCH PROFILE:" in prompt
        return '''```json
{"relevance": 0.92, "potential_overlap": 0.81, "overlap_level": "high", "summary": "Relevant context-selection work.", "fit_reason": "Matches adaptive context selection.", "overlap_reason": "Potentially overlaps the planned research direction.", "suggested_tags": ["context", "sarcasm"]}
```'''


def test_parse_json_response_handles_code_fence():
    value = parse_json_response("```json\n{\"x\": 1}\n```")
    assert value["x"] == 1


def test_llm_assessment_is_structured():
    profile = KeywordProfile(groups=[], description="Adaptive context research")
    paper = Paper(source="test", title="Context paper", abstract="Abstract")
    score = Score(total=0.8, keyword_score=0.5, semantic_score=0.9, group_hits={})
    assessment = assess_paper(FakeProvider(), paper, score, profile)
    assert assessment.overlap_level == "high"
    assert assessment.relevance == 0.92
    assert assessment.potential_overlap == 0.81
