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
    INSERT INTO papers(source, title, title_normalized, doi) VALUES('test', 'Legacy', 'legacy', '10.1234/legacy');
    CREATE TABLE citation_fetches (
        paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
        provider TEXT NOT NULL,
        direction TEXT NOT NULL,
        fetched_at TEXT NOT NULL,
        result_count INTEGER NOT NULL DEFAULT 0,
        error_message TEXT NOT NULL DEFAULT '',
        PRIMARY KEY(paper_id, provider, direction)
    );
    """)
    conn.commit()
    conn.close()

    store = PaperStore(db)
    columns = {row[1] for row in store.conn.execute("PRAGMA table_info(papers)")}
    paper = store.conn.execute("SELECT id FROM papers WHERE title='Legacy'").fetchone()
    new_tables = {
        row[0] for row in store.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    identifiers = store.identifiers_for_paper(int(paper[0]))
    fetch_columns = {row[1] for row in store.conn.execute("PRAGMA table_info(citation_fetches)")}
    store.close()
    assert {"keyword_score", "semantic_score", "scoring_version", "llm_assessment_json"} <= columns
    assert {"paper_identifiers", "paper_relations", "citation_fetches"} <= new_tables
    assert identifiers["doi"] == ["10.1234/legacy"]
    assert "requested_limit" in fetch_columns
