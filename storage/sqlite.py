from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from sources.base import Paper, extract_arxiv_id

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    external_id TEXT,
    title TEXT NOT NULL,
    title_normalized TEXT NOT NULL,
    title_hash TEXT NOT NULL DEFAULT '',
    abstract TEXT NOT NULL DEFAULT '',
    authors_json TEXT NOT NULL DEFAULT '[]',
    published_at TEXT,
    updated_at TEXT,
    doi TEXT,
    doi_normalized TEXT,
    arxiv_id TEXT,
    url TEXT,
    pdf_url TEXT,
    venue TEXT,
    citation_count INTEGER NOT NULL DEFAULT 0,
    reference_count INTEGER,
    influential_citation_count INTEGER,
    relevance_score REAL NOT NULL DEFAULT 0,
    keyword_score REAL NOT NULL DEFAULT 0,
    semantic_score REAL,
    scoring_version TEXT NOT NULL DEFAULT 'keyword-v0.1',
    matched_groups_json TEXT NOT NULL DEFAULT '{}',
    raw_json TEXT NOT NULL DEFAULT '{}',
    source_refs_json TEXT NOT NULL DEFAULT '{}',
    source_tags_json TEXT NOT NULL DEFAULT '[]',
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
CREATE TABLE IF NOT EXISTS feedback_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    signal REAL NOT NULL,
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

"""

STATUSES = ("new", "to-read", "read", "archived", "dismissed")
SORT_CHOICES = (
    "relevance_score",
    "personalized",
    "recent",
    "published_oldest",
    "newest_added",
    "title",
    "score",
    "citations",
    "references",
    "influential_citations",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean_doi(value: str | None) -> str | None:
    if not value:
        return None
    value = str(value).strip()
    value = re.sub(r"^https?://doi.org/", "", value, flags=re.IGNORECASE)
    return value.casefold() or None


def _title_hash(title_normalized: str) -> str:
    return hashlib.sha256(title_normalized.encode("utf-8")).hexdigest()


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
            "title_hash": "ALTER TABLE papers ADD COLUMN title_hash TEXT NOT NULL DEFAULT ''",
            "doi_normalized": "ALTER TABLE papers ADD COLUMN doi_normalized TEXT",
            "arxiv_id": "ALTER TABLE papers ADD COLUMN arxiv_id TEXT",
            "source_refs_json": "ALTER TABLE papers ADD COLUMN source_refs_json TEXT NOT NULL DEFAULT '{}'",
            "source_tags_json": "ALTER TABLE papers ADD COLUMN source_tags_json TEXT NOT NULL DEFAULT '[]'",
            "reference_count": "ALTER TABLE papers ADD COLUMN reference_count INTEGER",
            "influential_citation_count": "ALTER TABLE papers ADD COLUMN influential_citation_count INTEGER",
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
        self.conn.execute("UPDATE papers SET last_seen_at=created_at WHERE last_seen_at=''")
        self.conn.execute("UPDATE papers SET status='new' WHERE status IS NULL OR status=''")

        # Backfill stable dedup identifiers for legacy records.
        rows = self.conn.execute(
            "SELECT id, title_normalized, title_hash, doi, doi_normalized, source, external_id, arxiv_id, source_refs_json FROM papers"
        ).fetchall()
        for row in rows:
            updates: dict[str, Any] = {}
            normalized_title = str(row["title_normalized"] or "").strip()
            if not row["title_hash"] and normalized_title:
                updates["title_hash"] = _title_hash(normalized_title)
            if not row["doi_normalized"] and row["doi"]:
                updates["doi_normalized"] = _clean_doi(row["doi"])
            arxiv_id = row["arxiv_id"]
            if not arxiv_id and str(row["source"] or "") == "arxiv":
                arxiv_id = extract_arxiv_id(row["external_id"])
            if not arxiv_id:
                try:
                    parsed_refs = json.loads(row["source_refs_json"] or "{}")
                    for ref in parsed_refs.values() if isinstance(parsed_refs, dict) else []:
                        candidate = ref.get("arxiv_id") if isinstance(ref, dict) else None
                        if candidate:
                            arxiv_id = str(candidate)
                            break
                except json.JSONDecodeError:
                    pass
            if arxiv_id and not row["arxiv_id"]:
                updates["arxiv_id"] = arxiv_id
            if not row["source_refs_json"] or row["source_refs_json"] == "{}":
                refs = {
                    str(row["source"]): {
                        "source": row["source"],
                        "external_id": row["external_id"],
                        "url": None,
                        "pdf_url": None,
                        **({"arxiv_id": arxiv_id} if arxiv_id else {}),
                    }
                }
                updates["source_refs_json"] = json.dumps(refs, ensure_ascii=False)
            if updates:
                assignments = ", ".join(f"{key}=?" for key in updates)
                self.conn.execute(
                    f"UPDATE papers SET {assignments} WHERE id=?",
                    (*updates.values(), row["id"]),
                )

        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_score ON papers(relevance_score DESC)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_date ON papers(published_at DESC)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_semantic ON papers(semantic_score DESC)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_doi_normalized ON papers(doi_normalized)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_doi_lower ON papers(lower(doi))")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_arxiv_id ON papers(arxiv_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_title_normalized ON papers(title_normalized)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_title_hash ON papers(title_hash)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_title_lower ON papers(lower(title))")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_citations ON papers(citation_count DESC)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_references ON papers(reference_count DESC)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_influential_citations ON papers(influential_citation_count DESC)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_paper ON feedback_events(paper_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_created ON feedback_events(created_at DESC)")
        self.conn.commit()
        self.fts_available = self._ensure_fts()

    def _ensure_fts(self) -> bool:
        """Initialize FTS5 full-text indexing, falling back cleanly if unavailable."""
        try:
            existing = self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='papers_fts'"
            ).fetchone() is not None
            self.conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5("
                "title, abstract, venue, notes, content='papers', content_rowid='id', tokenize='unicode61')"
            )
            self.conn.executescript(
                """
                CREATE TRIGGER IF NOT EXISTS papers_fts_ai AFTER INSERT ON papers BEGIN
                  INSERT INTO papers_fts(rowid, title, abstract, venue, notes)
                  VALUES (new.id, new.title, new.abstract, new.venue, new.notes);
                END;
                CREATE TRIGGER IF NOT EXISTS papers_fts_ad AFTER DELETE ON papers BEGIN
                  INSERT INTO papers_fts(papers_fts, rowid, title, abstract, venue, notes)
                  VALUES ('delete', old.id, old.title, old.abstract, old.venue, old.notes);
                END;
                CREATE TRIGGER IF NOT EXISTS papers_fts_au AFTER UPDATE OF title, abstract, venue, notes ON papers BEGIN
                  INSERT INTO papers_fts(papers_fts, rowid, title, abstract, venue, notes)
                  VALUES ('delete', old.id, old.title, old.abstract, old.venue, old.notes);
                  INSERT INTO papers_fts(rowid, title, abstract, venue, notes)
                  VALUES (new.id, new.title, new.abstract, new.venue, new.notes);
                END;
                """
            )
            if not existing:
                self.conn.execute("INSERT INTO papers_fts(papers_fts) VALUES('rebuild')")
            self.conn.commit()
            return True
        except sqlite3.OperationalError as exc:
            # FTS5 is optional in some custom SQLite builds. LIKE remains available.
            self.conn.rollback()
            if "fts5" not in str(exc).casefold() and "no such module" not in str(exc).casefold():
                raise
            return False

    @staticmethod
    def _fts_query(query: str) -> str:
        tokens = re.findall(r"[\w]+", query, flags=re.UNICODE)
        return " AND ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)

    def close(self) -> None:
        self.conn.close()

    @staticmethod
    def _paper_source_refs(paper: Paper) -> dict[str, dict[str, Any]]:
        refs: dict[str, Any] = {
            "source": paper.source,
            "external_id": paper.external_id,
            "url": paper.url,
            "pdf_url": paper.pdf_url,
        }
        refs.update(paper.identifiers)
        return {paper.source: refs}

    @staticmethod
    def _merge_json_mapping(existing_json: str | None, incoming: dict[str, Any]) -> dict[str, Any]:
        try:
            current = json.loads(existing_json or "{}")
            if not isinstance(current, dict):
                current = {}
        except json.JSONDecodeError:
            current = {}
        for key, value in incoming.items():
            current[key] = value
        return current

    @staticmethod
    def _merge_tags(existing_json: str | None, source_tags: list[str]) -> list[str]:
        try:
            existing = json.loads(existing_json or "[]")
        except json.JSONDecodeError:
            existing = []
        return sorted(
            {str(t).strip() for t in [*existing, *source_tags] if str(t).strip()},
            key=str.casefold,
        )

    def _find_duplicate(self, paper: Paper) -> sqlite3.Row | None:
        doi = _clean_doi(paper.doi)
        if doi:
            row = self.conn.execute(
                "SELECT * FROM papers WHERE doi_normalized=? ORDER BY id LIMIT 1", (doi,)
            ).fetchone()
            if row:
                return row

        arxiv_id = paper.identifiers.get("arxiv_id")
        if not arxiv_id and paper.source == "arxiv":
            arxiv_id = extract_arxiv_id(paper.external_id)
        if arxiv_id:
            row = self.conn.execute(
                "SELECT * FROM papers WHERE lower(arxiv_id)=lower(?) ORDER BY id LIMIT 1", (arxiv_id,)
            ).fetchone()
            if row:
                return row

        title_hash = paper.title_hash
        if title_hash:
            row = self.conn.execute(
                "SELECT * FROM papers WHERE title_hash=? ORDER BY id LIMIT 1", (title_hash,)
            ).fetchone()
            if row:
                return row
        return None

    def _upsert_paper_no_commit(
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
        existing = self._find_duplicate(paper)
        doi_normalized = _clean_doi(paper.doi)
        arxiv_id = paper.identifiers.get("arxiv_id")
        if not arxiv_id and paper.source == "arxiv":
            arxiv_id = extract_arxiv_id(paper.external_id)
        source_refs = self._paper_source_refs(paper)

        if existing:
            merged_refs = self._merge_json_mapping(existing["source_refs_json"], source_refs)
            merged_source_tags = self._merge_tags(existing["source_tags_json"], paper.source_tags)

            # Prefer non-empty/new metadata, but never clobber good existing values with blanks.
            authors = paper.authors or json.loads(existing["authors_json"] or "[]")
            abstract = paper.abstract or existing["abstract"] or ""
            published_at = paper.published_at or existing["published_at"]
            updated_at = paper.updated_at or existing["updated_at"]
            venue = paper.venue or existing["venue"]
            url = paper.url or existing["url"]
            pdf_url = paper.pdf_url or existing["pdf_url"]
            doi = paper.doi or existing["doi"]
            source_external_id = paper.external_id or existing["external_id"]
            source_name = existing["source"] or paper.source

            self.conn.execute(
                """
                UPDATE papers SET
                  source=?, external_id=?, title=?, title_normalized=?, title_hash=?, abstract=?,
                  authors_json=?, published_at=?, updated_at=?, doi=?, doi_normalized=?, arxiv_id=?,
                  url=?, pdf_url=?, venue=?, citation_count=MAX(citation_count, ?),
                  reference_count=COALESCE(?, reference_count),
                  influential_citation_count=COALESCE(?, influential_citation_count),
                  relevance_score=?, keyword_score=?, semantic_score=?, scoring_version=?,
                  matched_groups_json=?, raw_json=?, source_refs_json=?, source_tags_json=?,
                  last_seen_at=?
                WHERE id=?
                """,
                (
                    source_name,
                    source_external_id,
                    paper.title or existing["title"],
                    paper.title_normalized or existing["title_normalized"],
                    paper.title_hash or existing["title_hash"],
                    abstract,
                    json.dumps(authors, ensure_ascii=False),
                    published_at,
                    updated_at,
                    doi,
                    doi_normalized or existing["doi_normalized"],
                    arxiv_id or existing["arxiv_id"],
                    url,
                    pdf_url,
                    venue,
                    int(paper.citation_count or 0),
                    paper.reference_count,
                    paper.influential_citation_count,
                    relevance_score,
                    keyword_score if keyword_score is not None else relevance_score,
                    semantic_score,
                    scoring_version,
                    json.dumps(matched_groups, ensure_ascii=False),
                    json.dumps(paper.raw, ensure_ascii=False, default=str),
                    json.dumps(merged_refs, ensure_ascii=False),
                    json.dumps(merged_source_tags, ensure_ascii=False),
                    now,
                    existing["id"],
                ),
            )
            return int(existing["id"])

        source_tags = sorted(set(paper.source_tags), key=str.casefold)
        cursor = self.conn.execute(
            """
            INSERT INTO papers (
              source, external_id, title, title_normalized, title_hash, abstract, authors_json,
              published_at, updated_at, doi, doi_normalized, arxiv_id, url, pdf_url, venue,
              citation_count, reference_count, influential_citation_count,
              relevance_score, keyword_score, semantic_score, scoring_version,
              matched_groups_json, raw_json, source_refs_json, source_tags_json,
              created_at, last_seen_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
            """,
            (
                paper.source,
                paper.external_id,
                paper.title,
                paper.title_normalized,
                paper.title_hash,
                paper.abstract,
                json.dumps(paper.authors, ensure_ascii=False),
                paper.published_at,
                paper.updated_at,
                paper.doi,
                doi_normalized,
                arxiv_id,
                paper.url,
                paper.pdf_url,
                paper.venue,
                int(paper.citation_count or 0),
                paper.reference_count,
                paper.influential_citation_count,
                relevance_score,
                keyword_score if keyword_score is not None else relevance_score,
                semantic_score,
                scoring_version,
                json.dumps(matched_groups, ensure_ascii=False),
                json.dumps(paper.raw, ensure_ascii=False, default=str),
                json.dumps(source_refs, ensure_ascii=False),
                json.dumps(source_tags, ensure_ascii=False),
                now,
                now,
            ),
        )
        return int(cursor.lastrowid)

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
        with self.conn:
            return self._upsert_paper_no_commit(
                paper,
                relevance_score=relevance_score,
                matched_groups=matched_groups,
                keyword_score=keyword_score,
                semantic_score=semantic_score,
                scoring_version=scoring_version,
            )

    def upsert_papers(self, rows: Iterable[tuple[Paper, float, dict[str, list[str]], float | None, float | None, str]]) -> list[int]:
        ids: list[int] = []
        with self.conn:
            for paper, relevance_score, matched_groups, keyword_score, semantic_score, scoring_version in rows:
                ids.append(
                    self._upsert_paper_no_commit(
                        paper,
                        relevance_score=relevance_score,
                        matched_groups=matched_groups,
                        keyword_score=keyword_score,
                        semantic_score=semantic_score,
                        scoring_version=scoring_version,
                    )
                )
        return ids

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
            "relevance_score": "relevance_score DESC, citation_count DESC, published_at DESC, id DESC",
            "recent": "published_at DESC, relevance_score DESC, id DESC",
            "published_oldest": "published_at ASC, relevance_score DESC, id ASC",
            "newest_added": "created_at DESC, id DESC",
            "title": "lower(title) ASC, id ASC",
            "score": "relevance_score DESC, citation_count DESC, published_at DESC, id DESC",
            "citations": "citation_count DESC, relevance_score DESC, published_at DESC, id DESC",
            "references": "reference_count DESC, relevance_score DESC, published_at DESC, id DESC",
            "influential_citations": "influential_citation_count DESC, relevance_score DESC, published_at DESC, id DESC",
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
            fts_query = self._fts_query(query) if getattr(self, "fts_available", False) else ""
            if fts_query:
                where.append("id IN (SELECT rowid FROM papers_fts WHERE papers_fts MATCH ?)")
                params.append(fts_query)
            else:
                where.append("(lower(title) LIKE lower(?) OR lower(abstract) LIKE lower(?) OR lower(venue) LIKE lower(?) OR lower(notes) LIKE lower(?))")
                pattern = f"%{query}%"
                params.extend([pattern, pattern, pattern, pattern])
        if tag:
            where.append("(lower(tags_json) LIKE lower(?) OR lower(source_tags_json) LIKE lower(?))")
            tag_pattern = f'%"{tag.casefold()}"%'
            params.extend([tag_pattern, tag_pattern])
        if min_score is not None:
            where.append("relevance_score>=?")
            params.append(float(min_score))

        sql = "SELECT * FROM papers"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += f" ORDER BY {order} LIMIT ?"
        params.append(max(1, int(limit)))
        return list(self.conn.execute(sql, params))

    def total_count(
        self,
        *,
        status: str | None = None,
        query: str | None = None,
        tag: str | None = None,
        min_score: float | None = None,
    ) -> int:
        where: list[str] = []
        params: list[Any] = []
        if status and status != "all":
            if status not in STATUSES:
                raise ValueError(f"Unsupported status: {status}")
            where.append("status=?")
            params.append(status)
        if query:
            fts_query = self._fts_query(query) if getattr(self, "fts_available", False) else ""
            if fts_query:
                where.append("id IN (SELECT rowid FROM papers_fts WHERE papers_fts MATCH ?)")
                params.append(fts_query)
            else:
                where.append("(lower(title) LIKE lower(?) OR lower(abstract) LIKE lower(?) OR lower(venue) LIKE lower(?) OR lower(notes) LIKE lower(?))")
                pattern = f"%{query}%"
                params.extend([pattern, pattern, pattern, pattern])
        if tag:
            pattern = f'%"{tag.casefold()}"%'
            where.append("(lower(tags_json) LIKE lower(?) OR lower(source_tags_json) LIKE lower(?))")
            params.extend([pattern, pattern])
        if min_score is not None:
            where.append("relevance_score>=?")
            params.append(float(min_score))
        sql = "SELECT COUNT(*) AS n FROM papers"
        if where:
            sql += " WHERE " + " AND ".join(where)
        return int(self.conn.execute(sql, params).fetchone()["n"])

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

    @staticmethod
    def _normalized_tags(tags: Iterable[str]) -> list[str]:
        values = {str(tag).strip() for tag in tags if str(tag).strip()}
        return sorted(values, key=str.casefold)

    def add_tags(self, paper_id: int, tags: Iterable[str]) -> None:
        row = self.get(paper_id)
        if row is None:
            raise KeyError(paper_id)
        current = json.loads(row["tags_json"] or "[]")
        self.set_tags(paper_id, [*current, *tags])

    def remove_tags(self, paper_id: int, tags: Iterable[str]) -> None:
        row = self.get(paper_id)
        if row is None:
            raise KeyError(paper_id)
        remove = {str(tag).strip().casefold() for tag in tags if str(tag).strip()}
        current = json.loads(row["tags_json"] or "[]")
        self.set_tags(paper_id, [tag for tag in current if str(tag).casefold() not in remove])

    def set_tags(self, paper_id: int, tags: Iterable[str]) -> None:
        if self.get(paper_id) is None:
            raise KeyError(paper_id)
        value = self._normalized_tags(tags)
        self.conn.execute(
            "UPDATE papers SET tags_json=? WHERE id=?",
            (json.dumps(value, ensure_ascii=False), paper_id),
        )
        self.conn.commit()

    def all_tags(self, *, include_source: bool = True) -> list[str]:
        tags: set[str] = set()
        for row in self.conn.execute("SELECT tags_json, source_tags_json FROM papers"):
            tags.update(json.loads(row[0] or "[]"))
            if include_source:
                tags.update(json.loads(row[1] or "[]"))
        return sorted(tags, key=str.casefold)

    def source_tags(self, paper_id: int) -> list[str]:
        row = self.get(paper_id)
        if row is None:
            raise KeyError(paper_id)
        try:
            return sorted(json.loads(row["source_tags_json"] or "[]"), key=str.casefold)
        except json.JSONDecodeError:
            return []

    def set_notes(self, paper_id: int, notes: str) -> None:
        if self.get(paper_id) is None:
            raise KeyError(paper_id)
        self.conn.execute("UPDATE papers SET notes=? WHERE id=?", (notes, paper_id))
        self.conn.commit()

    def feedback_rows(self) -> list[sqlite3.Row]:
        """Return only fields needed to build the lightweight personal preference model."""
        return list(
            self.conn.execute(
                "SELECT status, dismiss_reason, matched_groups_json FROM papers "
                "WHERE status != 'new'"
            )
        )

    def record_feedback(self, paper_id: int, signal: float, *, reason: str = "") -> None:
        if self.get(paper_id) is None:
            raise KeyError(paper_id)
        signal = max(-1.0, min(1.0, float(signal)))
        self.conn.execute(
            "INSERT INTO feedback_events(paper_id, signal, reason, created_at) VALUES (?, ?, ?, ?)",
            (paper_id, signal, str(reason).strip(), _now()),
        )
        self.conn.commit()

    def feedback_count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) AS n FROM feedback_events").fetchone()["n"])

    def feedback_rows(self) -> list[sqlite3.Row]:
        """Return compact per-paper signals for the lightweight personal preference model."""
        return list(
            self.conn.execute(
                """
                SELECT p.status, p.dismiss_reason, p.matched_groups_json,
                       COALESCE(SUM(f.signal), 0.0) AS explicit_feedback
                FROM papers AS p
                LEFT JOIN feedback_events AS f ON f.paper_id = p.id
                WHERE p.status != 'new' OR f.id IS NOT NULL
                GROUP BY p.id
                """
            )
        )

    def stats(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT status, COUNT(*) AS n FROM papers GROUP BY status").fetchall()
        stats = {status: 0 for status in STATUSES}
        stats.update({str(row["status"]): int(row["n"]) for row in rows})
        stats["all"] = sum(stats.values())
        return stats
