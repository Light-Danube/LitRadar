from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ranking.keywords import KeywordProfile
from ranking.scoring import score_paper
from sources.base import Paper


def test_keyword_scoring_prefers_relevant_paper():
    profile = KeywordProfile.from_json(ROOT / "research_profile.json")
    relevant = Paper(source="test", title="Task-dependent context selection for sarcasm and emotion", abstract="Adaptive context modeling for online conversations.")
    irrelevant = Paper(source="test", title="A survey of image segmentation", abstract="Medical computer vision and semantic segmentation.")
    assert score_paper(relevant, profile).total > score_paper(irrelevant, profile).total


def test_title_normalization():
    paper = Paper(source="test", title="  Hello   WORLD  ")
    assert paper.title_normalized == "hello world"
