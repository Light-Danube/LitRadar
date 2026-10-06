from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sources.base import Paper
from storage.sqlite import PaperStore


def test_store_deduplicates_by_title(tmp_path: Path):
    db = tmp_path / "test.sqlite3"
    store = PaperStore(db)
    paper = Paper(source="a", title="Same Paper", abstract="A")
    first = store.upsert_paper(paper, relevance_score=1.0, matched_groups={"emotion": ["emotion"]})
    second = store.upsert_paper(Paper(source="b", title="Same Paper", abstract="B"), relevance_score=2.0, matched_groups={"sarcasm": ["sarcasm"]})
    rows = store.top(10)
    store.close()
    assert first == second
    assert len(rows) == 1
    assert rows[0]["relevance_score"] == 2.0
