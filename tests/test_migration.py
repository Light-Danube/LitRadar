from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from storage.sqlite import PaperStore


def test_v01_database_is_migrated(tmp_path: Path):
    db = tmp_path / "legacy.sqlite3"
    conn = sqlite3.connect(db)
    conn.executescript("""
    CREATE TABLE papers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        external_id TEXT,
        title TEXT NOT NULL,
        title_normalized TEXT NOT NULL,
        abstract TEXT NOT NULL DEFAULT '',
        authors_json TEXT NOT NULL DEFAULT '[]',
        published_at TEXT,
        updated_at TEXT,
        doi TEXT,
        url TEXT,
        pdf_url TEXT,
        venue TEXT,
        citation_count INTEGER NOT NULL DEFAULT 0,
        relevance_score REAL NOT NULL DEFAULT 0,
        matched_groups_json TEXT NOT NULL DEFAULT '{}',
        raw_json TEXT NOT NULL DEFAULT '{}'
    );
    INSERT INTO papers(source, title, title_normalized) VALUES('test', 'Legacy', 'legacy');
    """)
    conn.commit()
    conn.close()

    store = PaperStore(db)
    columns = {row[1] for row in store.conn.execute("PRAGMA table_info(papers)")}
    store.close()
    assert {"keyword_score", "semantic_score", "scoring_version", "llm_assessment_json"} <= columns
