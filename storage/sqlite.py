from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from sources.base import Paper

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
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
    keyword_score REAL NOT NULL DEFAULT 0,
    semantic_score REAL,
    scoring_version TEXT NOT NULL DEFAULT 'keyword-v0.1',
    matched_groups_json TEXT NOT NULL DEFAULT '{}',
    raw_json TEXT NOT NULL DEFAULT '{}',
    llm_assessment_json TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    tags_json TEXT NOT NULL DEFAULT '[]',
    notes TEXT NOT NULL DEFAULT '',
    dismiss_reason TEXT,
    created_at TEXT NOT NULL DEFAULT '',
    last_seen_at TEXT NOT NULL DEFAULT '',
    read_at TEXT,
    archived_at TEXT,
    dismissed_at TEXT
);
"""

STATUSES = ("new", "to-read", "read", "archived", "dismissed")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PaperStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(papers)")}
        migrations = {
            "keyword_score": "ALTER TABLE papers ADD COLUMN keyword_score REAL NOT NULL DEFAULT 0",
            "semantic_score": "ALTER TABLE papers ADD COLUMN semantic_score REAL",
            "scoring_version": "ALTER TABLE papers ADD COLUMN scoring_version TEXT NOT NULL DEFAULT 'keyword-v0.1'",
            "llm_assessment_json": "ALTER TABLE papers ADD COLUMN llm_assessment_json TEXT",
            "status": "ALTER TABLE papers ADD COLUMN status TEXT NOT NULL DEFAULT 'new'",
            "tags_json": "ALTER TABLE papers ADD COLUMN tags_json TEXT NOT NULL DEFAULT '[]'",
            "notes": "ALTER TABLE papers ADD COLUMN notes TEXT NOT NULL DEFAULT ''",
            "dismiss_reason": "ALTER TABLE papers ADD COLUMN dismiss_reason TEXT",
            "created_at": "ALTER TABLE papers ADD COLUMN created_at TEXT NOT NULL DEFAULT ''",
            "last_seen_at": "ALTER TABLE papers ADD COLUMN last_seen_at TEXT NOT NULL DEFAULT ''",
            "read_at": "ALTER TABLE papers ADD COLUMN read_at TEXT",
            "archived_at": "ALTER TABLE papers ADD COLUMN archived_at TEXT",
            "dismissed_at": "ALTER TABLE papers ADD COLUMN dismissed_at TEXT",
        }
        for name, statement in migrations.items():
            if name not in columns:
                self.conn.execute(statement)

        now = _now()
        self.conn.execute("UPDATE papers SET created_at=? WHERE created_at=''", (now,))
        self.conn.execute("UPDATE papers SET last_seen_at=created_at WHERE last_seen_at=''",)
        self.conn.execute(
            "UPDATE papers SET status='new' WHERE status IS NULL OR status=''"
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_score ON papers(relevance_score DESC)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_date ON papers(published_at DESC)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_semantic ON papers(semantic_score DESC)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi)")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def upsert_paper(
        self,
        paper: Paper,
        *,
        relevance_score: float,
        matched_groups: dict[str, list[str]],
        keyword_score: float | None = None,
        semantic_score: float | None = None,
        scoring_version: str = "keyword-v0.1",
    ) -> int:
        now = _now()
        payload = (
            paper.source,
            paper.external_id,
            paper.title,
            paper.title_normalized,
            paper.abstract,
            json.dumps(paper.authors, ensure_ascii=False),
            paper.published_at,
            paper.updated_at,
            paper.doi,
            paper.url,
            paper.pdf_url,
            paper.venue,
            paper.citation_count,
            relevance_score,
            keyword_score if keyword_score is not None else relevance_score,
            semantic_score,
            scoring_version,
            json.dumps(matched_groups, ensure_ascii=False),
            json.dumps(paper.raw, ensure_ascii=False, default=str),
        )
        existing = None
        if paper.doi:
            existing = self.conn.execute(
                "SELECT id FROM papers WHERE lower(doi)=lower(?)", (paper.doi,)
            ).fetchone()
        if existing is None:
            existing = self.conn.execute(
                "SELECT id FROM papers WHERE title_normalized=?", (paper.title_normalized,)
            ).fetchone()

        if existing:
            self.conn.execute(
                """
                UPDATE papers SET
                  source=?, external_id=?, title=?, title_normalized=?, abstract=?,
                  authors_json=?, published_at=?, updated_at=?, doi=?, url=?, pdf_url=?,
                  venue=?, citation_count=?, relevance_score=?, keyword_score=?, semantic_score=?,
                  scoring_version=?, matched_groups_json=?, raw_json=?, last_seen_at=?
                WHERE id=?
                """,
                payload + (now, existing[0]),
            )
            self.conn.commit()
            return int(existing[0])

        cursor = self.conn.execute(
            """
            INSERT INTO papers (
              source, external_id, title, title_normalized, abstract, authors_json,
              published_at, updated_at, doi, url, pdf_url, venue, citation_count,
              relevance_score, keyword_score, semantic_score, scoring_version,
              matched_groups_json, raw_json, created_at, last_seen_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
            """,
            payload + (now, now),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def set_llm_assessment(self, paper_id: int, assessment: dict[str, Any]) -> None:
        self.conn.execute(
            "UPDATE papers SET llm_assessment_json=? WHERE id=?",
            (json.dumps(assessment, ensure_ascii=False), paper_id),
        )
        self.conn.commit()

    def get(self, paper_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM papers WHERE id=?", (paper_id,)).fetchone()

    def list_papers(
        self,
        *,
        limit: int = 50,
        status: str | None = None,
        query: str | None = None,
        tag: str | None = None,
        min_score: float | None = None,
        sort: str = "relevance_score",
    ) -> list[sqlite3.Row]:
        order_map = {
            "relevance_score": "relevance_score DESC, citation_count DESC, published_at DESC",
            "recent": "published_at DESC, relevance_score DESC",
            "newest_added": "created_at DESC",
            "title": "lower(title) ASC",
            "score": "relevance_score DESC",
        }
        order = order_map.get(sort)
        if order is None:
            raise ValueError(f"Unsupported sort: {sort}")

        where: list[str] = []
        params: list[Any] = []
        if status and status != "all":
            if status not in STATUSES:
                raise ValueError(f"Unsupported status: {status}")
            where.append("status=?")
            params.append(status)
        if query:
            where.append("(lower(title) LIKE lower(?) OR lower(abstract) LIKE lower(?) OR lower(venue) LIKE lower(?))")
            pattern = f"%{query}%"
            params.extend([pattern, pattern, pattern])
        if tag:
            where.append("lower(tags_json) LIKE lower(?)")
            params.append(f'%"{tag.casefold()}"%')
        if min_score is not None:
            where.append("relevance_score>=?")
            params.append(float(min_score))

        sql = "SELECT * FROM papers"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += f" ORDER BY {order} LIMIT ?"
        params.append(max(1, int(limit)))
        return list(self.conn.execute(sql, params))

    def top(self, limit: int = 10, *, sort: str = "relevance_score") -> list[sqlite3.Row]:
        return self.list_papers(limit=limit, sort=sort)

    def recent(self, limit: int = 10) -> list[sqlite3.Row]:
        return self.list_papers(limit=limit, sort="recent")

    def set_status(self, paper_id: int, status: str, *, dismiss_reason: str | None = None) -> None:
        if status not in STATUSES:
            raise ValueError(f"Unsupported status: {status}")
        row = self.get(paper_id)
        if row is None:
            raise KeyError(paper_id)
        now = _now()
        read_at = row["read_at"]
        archived_at = row["archived_at"]
        dismissed_at = row["dismissed_at"]

        if status == "read":
            read_at = read_at or now
            archived_at = None
            dismissed_at = None
        elif status == "archived":
            archived_at = archived_at or now
            dismissed_at = None
        elif status == "dismissed":
            dismissed_at = dismissed_at or now
        elif status in {"new", "to-read"}:
            archived_at = None
            dismissed_at = None

        reason = dismiss_reason if status == "dismissed" else None
        self.conn.execute(
            """
            UPDATE papers
            SET status=?, dismiss_reason=?, read_at=?, archived_at=?, dismissed_at=?
            WHERE id=?
            """,
            (status, reason, read_at, archived_at, dismissed_at, paper_id),
        )
        self.conn.commit()

    def add_tags(self, paper_id: int, tags: Iterable[str]) -> None:
        row = self.get(paper_id)
        if row is None:
            raise KeyError(paper_id)
        current = json.loads(row["tags_json"] or "[]")
        normalized = {str(tag).strip() for tag in current if str(tag).strip()}
        normalized.update(str(tag).strip() for tag in tags if str(tag).strip())
        value = sorted(normalized, key=str.casefold)
        self.conn.execute("UPDATE papers SET tags_json=? WHERE id=?", (json.dumps(value, ensure_ascii=False), paper_id))
        self.conn.commit()

    def set_notes(self, paper_id: int, notes: str) -> None:
        if self.get(paper_id) is None:
            raise KeyError(paper_id)
        self.conn.execute("UPDATE papers SET notes=? WHERE id=?", (notes, paper_id))
        self.conn.commit()

    def stats(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT status, COUNT(*) AS n FROM papers GROUP BY status").fetchall()
        stats = {status: 0 for status in STATUSES}
        stats.update({str(row["status"]): int(row["n"]) for row in rows})
        stats["all"] = sum(stats.values())
        return stats
