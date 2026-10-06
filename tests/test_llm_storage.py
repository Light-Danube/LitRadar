from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sources.base import Paper
from storage.sqlite import PaperStore


def test_llm_assessment_is_persisted(tmp_path: Path):
    store = PaperStore(tmp_path / "radar.sqlite3")
    paper_id = store.upsert_paper(
        Paper(source="test", title="Assessment paper"),
        relevance_score=0.8,
        keyword_score=0.5,
        semantic_score=0.9,
        matched_groups={"emotion": ["emotion recognition"]},
        scoring_version="semantic-v0.2:test",
    )
    store.set_llm_assessment(
        paper_id,
        {"relevance": 0.9, "potential_overlap": 0.7, "overlap_level": "medium"},
    )
    row = store.get(paper_id)
    store.close()
    assert json.loads(row["llm_assessment_json"])["overlap_level"] == "medium"
