from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ranking.keywords import KeywordProfile
from ranking.scoring import score_papers_semantic
from sources.base import Paper


class FakeEmbedder:
    model_name = "fake-vectors"

    def __init__(self):
        self.vectors = {
            "profile": np.array([1.0, 0.0], dtype=np.float32),
            "relevant": np.array([0.95, 0.1], dtype=np.float32),
            "irrelevant": np.array([0.0, 1.0], dtype=np.float32),
        }

    def encode(self, texts):
        out = []
        for text in texts:
            if text == "PROFILE":
                out.append(self.vectors["profile"])
            elif text.casefold().startswith("relevant "):
                out.append(self.vectors["relevant"])
            else:
                out.append(self.vectors["irrelevant"])
        return np.stack(out)


def test_semantic_ranking_can_outweigh_weak_keywords():
    profile = KeywordProfile(
        groups=[],
        name="test",
        description="PROFILE",
        keyword_weight=0.35,
        semantic_weight=0.65,
    )
    relevant = Paper(source="test", title="Relevant paper", abstract="This is semantically relevant.")
    irrelevant = Paper(source="test", title="Irrelevant paper", abstract="Unrelated material.")
    ranked = score_papers_semantic([irrelevant, relevant], profile, FakeEmbedder())
    assert ranked[0][0].title == "Relevant paper"
    assert ranked[0][1].semantic_score > ranked[1][1].semantic_score
    assert ranked[0][1].scoring_version.startswith("semantic-v0.2")
