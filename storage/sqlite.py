from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import nullcontext
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
CREATE TABLE IF NOT EXISTS paper_identifiers (
    identifier_type TEXT NOT NULL,
    identifier_value TEXT NOT NULL,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    source TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    PRIMARY KEY(identifier_type, identifier_value)
);
CREATE INDEX IF NOT EXISTS idx_paper_identifiers_paper ON paper_identifiers(paper_id);
CREATE TABLE IF NOT EXISTS paper_relations (
    source_paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    target_paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL CHECK(relation_type IN ('cites', 'related')),
    provider TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    PRIMARY KEY(source_paper_id, target_paper_id, relation_type, provider),
    CHECK(source_paper_id <> target_paper_id)
);
CREATE INDEX IF NOT EXISTS idx_paper_relations_target ON paper_relations(target_paper_id, relation_type);
CREATE TABLE IF NOT EXISTS citation_fetches (
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    direction TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    result_count INTEGER NOT NULL DEFAULT 0,
    requested_limit INTEGER NOT NULL DEFAULT 0,
    error_message TEXT NOT NULL DEFAULT '',
    PRIMARY KEY(paper_id, provider, direction)
);
CREATE TABLE IF NOT EXISTS research_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    status TEXT NOT NULL,
    summary_json TEXT NOT NULL DEFAULT '{}',
    error_message TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_research_runs_started ON research_runs(started_at DESC);
CREATE TABLE IF NOT EXISTS digest_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL,
    period TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    sent_at TEXT,
    since_at TEXT NOT NULL,
    paper_ids_json TEXT NOT NULL DEFAULT '[]',
    output_path TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    error_message TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_digest_deliveries_sent ON digest_deliveries(channel, sent_at DESC);
CREATE TABLE IF NOT EXISTS digest_delivery_papers (
    delivery_id INTEGER NOT NULL REFERENCES digest_deliveries(id) ON DELETE CASCADE,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    PRIMARY KEY(delivery_id, paper_id)
);
CREATE INDEX IF NOT EXISTS idx_digest_delivery_papers_paper ON digest_delivery_papers(paper_id);
CREATE TABLE IF NOT EXISTS discovery_venues (
    source_id TEXT PRIMARY KEY,
    metadata_json TEXT NOT NULL,
    retrieved_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS paper_venue_observations (
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES discovery_venues(source_id),
    observation_json TEXT NOT NULL,
    PRIMARY KEY(paper_id, source_id)
);
CREATE TABLE IF NOT EXISTS venue_search_cache (
    cache_key TEXT PRIMARY KEY,
    retrieved_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS paper_annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    channel TEXT NOT NULL CHECK(channel IN ('research_note', 'annotation')),
    kind TEXT NOT NULL CHECK(kind IN ('user', 'imported', 'extracted', 'generated', 'legacy')),
    content TEXT NOT NULL,
    source_ref TEXT,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_annotations_paper_channel ON paper_annotations(paper_id, channel, id DESC);
CREATE TABLE IF NOT EXISTS annotation_revisions (
    annotation_id INTEGER NOT NULL REFERENCES paper_annotations(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL,
    content TEXT NOT NULL,
    review_status TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    PRIMARY KEY(annotation_id, revision)
);

"""

STATUSES = ("new", "to-read", "read", "archived", "dismissed")
ANNOTATION_KINDS = ("user", "imported", "extracted", "generated")
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
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value, flags=re.IGNORECASE)
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

        annotation_columns = {row[1] for row in self.conn.execute("PRAGMA table_info(paper_annotations)")}
        for name, definition in {
            "origin_method": "TEXT NOT NULL DEFAULT 'declared'",
            "review_status": "TEXT NOT NULL DEFAULT 'unreviewed'",
            "revision": "INTEGER NOT NULL DEFAULT 1",
            "updated_at": "TEXT",
            "evidence_key": "TEXT",
            "deleted_at": "TEXT",
        }.items():
            if name not in annotation_columns:
                self.conn.execute(f"ALTER TABLE paper_annotations ADD COLUMN {name} {definition}")
        self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_annotation_evidence "
                          "ON paper_annotations(paper_id, evidence_key) WHERE evidence_key IS NOT NULL")
        self.conn.execute(
            "INSERT OR IGNORE INTO annotation_revisions(annotation_id, revision, content, review_status, recorded_at) SELECT id, revision, content, review_status, "
            "COALESCE(updated_at, recorded_at) FROM paper_annotations WHERE channel='annotation'"
        )
        revision_columns = {row[1] for row in self.conn.execute("PRAGMA table_info(annotation_revisions)")}
        if "deleted_at" not in revision_columns:
            self.conn.execute("ALTER TABLE annotation_revisions ADD COLUMN deleted_at TEXT")

        fetch_columns = {row[1] for row in self.conn.execute("PRAGMA table_info(citation_fetches)")}
        if "requested_limit" not in fetch_columns:
            self.conn.execute(
                "ALTER TABLE citation_fetches ADD COLUMN requested_limit INTEGER NOT NULL DEFAULT 0"
            )

        now = _now()
        self.conn.execute("UPDATE papers SET created_at=? WHERE created_at=''", (now,))
        self.conn.execute("UPDATE papers SET last_seen_at=created_at WHERE last_seen_at=''")
        self.conn.execute("UPDATE papers SET status='new' WHERE status IS NULL OR status=''")
        # Existing note authorship/time is unknown; never invent user provenance.
        self.conn.execute(
            "INSERT INTO paper_annotations(paper_id, channel, kind, content, recorded_at) "
            "SELECT id, 'research_note', 'legacy', notes, ? FROM papers p "
            "WHERE notes<>'' AND NOT EXISTS (SELECT 1 FROM paper_annotations a "
            "WHERE a.paper_id=p.id AND a.channel='research_note')",
            (now,),
        )

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

        # Backfill cross-source identifiers once for libraries created before v0.6.
        identifier_rows = self.conn.execute(
            "SELECT id, source, external_id, doi, arxiv_id, source_refs_json FROM papers ORDER BY id"
        ).fetchall()
        for row in identifier_rows:
            identifiers = self._identifiers_from_stored_row(row)
            for identifier_type, identifier_value in identifiers:
                self.conn.execute(
                    "INSERT OR IGNORE INTO paper_identifiers(identifier_type, identifier_value, paper_id, source, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (identifier_type, identifier_value, row["id"], row["source"] or "", now),
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

    @staticmethod
    def _normalize_identifier(identifier_type: str, value: Any) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        kind = identifier_type.casefold().strip()
        if kind == "doi":
            text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text, flags=re.IGNORECASE)
            text = re.sub(r"^doi:\s*", "", text, flags=re.IGNORECASE)
            return text.casefold().strip() or None
        if kind == "arxiv_id":
            text = extract_arxiv_id(text) or ""
            text = re.sub(r"v\d+$", "", text, flags=re.IGNORECASE)
            return text.casefold() or None
        if kind == "openalex_id":
            text = text.rstrip("/").rsplit("/", 1)[-1]
        elif kind in {"semantic_scholar_id", "corpus_id", "pmid", "pmcid"}:
            text = text.rsplit("/", 1)[-1]
        return text.casefold() or None

    @classmethod
    def _identifiers_from_stored_row(cls, row) -> list[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        def add(kind: str, value: Any) -> None:
            normalized = cls._normalize_identifier(kind, value)
            if normalized:
                pairs.add((kind, normalized))

        add("doi", row["doi"])
        add("arxiv_id", row["arxiv_id"])
        source = str(row["source"] or "").casefold()
        if source == "openalex":
            add("openalex_id", row["external_id"])
        elif source == "semantic_scholar":
            add("semantic_scholar_id", row["external_id"])
        elif source == "arxiv":
            add("arxiv_id", row["external_id"])
        try:
            refs = json.loads(row["source_refs_json"] or "{}")
        except (json.JSONDecodeError, TypeError):
            refs = {}
        key_aliases = {
            "doi": "doi", "openalex_id": "openalex_id", "semantic_scholar_id": "semantic_scholar_id",
            "s2_id": "semantic_scholar_id", "arxiv_id": "arxiv_id", "pmid": "pmid",
            "pmcid": "pmcid", "corpus_id": "corpus_id",
        }
        if isinstance(refs, dict):
            for source_name, ref in refs.items():
                if not isinstance(ref, dict):
                    continue
                ref_source = str(ref.get("source") or source_name).casefold()
                external_id = ref.get("external_id")
                if external_id:
                    if ref_source == "openalex":
                        add("openalex_id", external_id)
                    elif ref_source == "semantic_scholar":
                        add("semantic_scholar_id", external_id)
                    elif ref_source == "arxiv":
                        add("arxiv_id", external_id)
                for key, value in ref.items():
                    identifier_type = key_aliases.get(str(key).casefold())
                    if identifier_type:
                        add(identifier_type, value)
        return sorted(pairs)

    @classmethod
    def _identifiers_for_paper(cls, paper: Paper) -> list[tuple[str, str]]:
        pairs: set[tuple[str, str]] = set()
        def add(kind: str, value: Any) -> None:
            normalized = cls._normalize_identifier(kind, value)
            if normalized:
                pairs.add((kind, normalized))

        add("doi", paper.doi)
        if paper.source == "openalex":
            add("openalex_id", paper.external_id)
        elif paper.source == "semantic_scholar":
            add("semantic_scholar_id", paper.external_id)
        elif paper.source == "arxiv":
            add("arxiv_id", paper.external_id)
        aliases = {
            "doi": "doi", "openalex_id": "openalex_id", "semantic_scholar_id": "semantic_scholar_id",
            "s2_id": "semantic_scholar_id", "arxiv_id": "arxiv_id", "pmid": "pmid",
            "pmcid": "pmcid", "corpus_id": "corpus_id",
        }
        for key, value in (paper.identifiers or {}).items():
            kind = aliases.get(str(key).casefold())
            if kind:
                add(kind, value)
        return sorted(pairs)

    def _sync_identifiers(self, paper_id: int, paper: Paper) -> None:
        now = _now()
        for identifier_type, identifier_value in self._identifiers_for_paper(paper):
            self.conn.execute(
                "INSERT INTO paper_identifiers(identifier_type, identifier_value, paper_id, source, updated_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(identifier_type, identifier_value) DO UPDATE SET "
                "updated_at=excluded.updated_at",
                (identifier_type, identifier_value, paper_id, paper.source, now),
            )

    def identifiers_for_paper(self, paper_id: int) -> dict[str, list[str]]:
        rows = self.conn.execute(
            "SELECT identifier_type, identifier_value FROM paper_identifiers WHERE paper_id=? ORDER BY identifier_type, identifier_value",
            (paper_id,),
        ).fetchall()
        result: dict[str, list[str]] = {}
        for row in rows:
            result.setdefault(str(row["identifier_type"]), []).append(str(row["identifier_value"]))
        return result

    def has_fresh_citation_fetch(
        self,
        paper_id: int,
        provider: str,
        direction: str,
        ttl_seconds: int,
        *,
        requested_limit: int | None = None,
        force: bool = False,
    ) -> bool:
        if force or ttl_seconds <= 0:
            return False
        row = self.conn.execute(
            "SELECT fetched_at, error_message, requested_limit FROM citation_fetches WHERE paper_id=? AND provider=? AND direction=?",
            (paper_id, provider, direction),
        ).fetchone()
        if not row or not row["fetched_at"]:
            return False
        if requested_limit is not None and int(row["requested_limit"] or 0) < int(requested_limit):
            # A caller asking for more neighbors than the cached result window
            # must fetch again instead of silently reusing a narrower slice.
            return False
        try:
            fetched = datetime.fromisoformat(str(row["fetched_at"]))
            age = (datetime.now(timezone.utc) - fetched.astimezone(timezone.utc)).total_seconds()
        except (ValueError, TypeError):
            return False
        allowed_age = min(ttl_seconds, 900) if row["error_message"] else ttl_seconds
        return age >= 0 and age < allowed_age

    def record_citation_fetch(
        self,
        paper_id: int,
        provider: str,
        direction: str,
        result_count: int,
        error_message: str = "",
        *,
        requested_limit: int = 0,
    ) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO citation_fetches(paper_id, provider, direction, fetched_at, result_count, requested_limit, error_message) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(paper_id, provider, direction) DO UPDATE SET "
                "fetched_at=excluded.fetched_at, result_count=excluded.result_count, "
                "requested_limit=MAX(citation_fetches.requested_limit, excluded.requested_limit), "
                "error_message=excluded.error_message",
                (paper_id, provider, direction, _now(), int(result_count), max(0, int(requested_limit)), str(error_message)[:1000]),
            )

    def record_relation(self, source_paper_id: int, target_paper_id: int, relation_type: str, provider: str) -> bool:
        if source_paper_id == target_paper_id:
            return False
        if relation_type not in {"cites", "related"}:
            raise ValueError(f"Unsupported relation type: {relation_type}")
        if relation_type == "related":
            source_paper_id, target_paper_id = sorted((int(source_paper_id), int(target_paper_id)))
        cursor = self.conn.execute(
            "INSERT OR IGNORE INTO paper_relations(source_paper_id, target_paper_id, relation_type, provider, observed_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (source_paper_id, target_paper_id, relation_type, provider, _now()),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def relation_neighbors(self, paper_id: int, direction: str) -> list[sqlite3.Row]:
        if direction == "references":
            query = "SELECT DISTINCT p.*, 'reference' AS relation_label FROM paper_relations r JOIN papers p ON p.id=r.target_paper_id WHERE r.source_paper_id=? AND r.relation_type='cites' ORDER BY p.citation_count DESC, p.title COLLATE NOCASE"
        elif direction == "cited-by":
            query = "SELECT DISTINCT p.*, 'cited-by' AS relation_label FROM paper_relations r JOIN papers p ON p.id=r.source_paper_id WHERE r.target_paper_id=? AND r.relation_type='cites' ORDER BY p.citation_count DESC, p.title COLLATE NOCASE"
        elif direction == "related":
            query = "SELECT DISTINCT p.*, 'related' AS relation_label FROM paper_relations r JOIN papers p ON p.id=CASE WHEN r.source_paper_id=? THEN r.target_paper_id ELSE r.source_paper_id END WHERE r.relation_type='related' AND (r.source_paper_id=? OR r.target_paper_id=?) ORDER BY p.citation_count DESC, p.title COLLATE NOCASE"
        else:
            raise ValueError(f"Unsupported neighbor direction: {direction}")
        if direction == "related":
            return self.conn.execute(query, (paper_id, paper_id, paper_id)).fetchall()
        return self.conn.execute(query, (paper_id,)).fetchall()

    def relation_degrees_within(self, paper_ids: Iterable[int]) -> dict[int, int]:
        """Count distinct graph neighbors per node, ignoring duplicate provider edges."""
        ids = {int(value) for value in paper_ids}
        degrees = {value: 0 for value in ids}
        if len(ids) < 2:
            return degrees
        ordered_ids = sorted(ids)
        placeholders = ",".join("?" for _ in ordered_ids)
        rows = self.conn.execute(
            "SELECT source_paper_id, target_paper_id, relation_type FROM paper_relations "
            f"WHERE source_paper_id IN ({placeholders}) OR target_paper_id IN ({placeholders})",
            (*ordered_ids, *ordered_ids),
        ).fetchall()
        seen: set[tuple[int, int, str]] = set()
        for row in rows:
            source_id = int(row["source_paper_id"])
            target_id = int(row["target_paper_id"])
            if source_id not in ids or target_id not in ids:
                continue
            if row["relation_type"] == "related":
                source_id, target_id = sorted((source_id, target_id))
            edge_key = (source_id, target_id, str(row["relation_type"]))
            if edge_key in seen:
                continue
            seen.add(edge_key)
            degrees[source_id] += 1
            degrees[target_id] += 1
        return degrees

    def citation_relation_count(self, paper_id: int) -> int:
        row = self.conn.execute(
            "SELECT COUNT(DISTINCT CASE WHEN relation_type='related' THEN "
            "min(source_paper_id,target_paper_id)||':'||max(source_paper_id,target_paper_id) "
            "ELSE source_paper_id||':'||target_paper_id END) AS n FROM paper_relations "
            "WHERE source_paper_id=? OR target_paper_id=?",
            (paper_id, paper_id),
        ).fetchone()
        return int(row["n"] or 0)

    def find_existing_paper_id(self, paper: Paper) -> int | None:
        row = self._find_duplicate(paper)
        return int(row["id"]) if row else None

    def _find_duplicate(self, paper: Paper) -> sqlite3.Row | None:
        for identifier_type, identifier_value in self._identifiers_for_paper(paper):
            row = self.conn.execute(
                "SELECT p.* FROM paper_identifiers i JOIN papers p ON p.id=i.paper_id "
                "WHERE i.identifier_type=? AND i.identifier_value=? ORDER BY p.id LIMIT 1",
                (identifier_type, identifier_value),
            ).fetchone()
            if row:
                incoming_doi = _clean_doi(paper.doi)
                if incoming_doi and row["doi_normalized"] and incoming_doi != row["doi_normalized"]:
                    raise ValueError("Conflicting DOI for an existing provider identifier")
                return row

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
            if doi:
                # A matching title must not merge two records that have different
                # explicit DOIs (e.g. two similarly named versions/outputs).
                row = self.conn.execute(
                    "SELECT * FROM papers WHERE title_hash=? AND (doi_normalized IS NULL OR doi_normalized=?) "
                    "ORDER BY CASE WHEN doi_normalized=? THEN 0 ELSE 1 END, id LIMIT 1",
                    (title_hash, doi, doi),
                ).fetchone()
                if row:
                    return row
            else:
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
            self._sync_identifiers(int(existing["id"]), paper)
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
        paper_id = int(cursor.lastrowid)
        self._sync_identifiers(paper_id, paper)
        return paper_id

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
        row = self.get(paper_id)
        if row is None:
            raise KeyError(paper_id)
        if row["notes"] == notes:
            return
        # Keep the legacy notes field and its revision in one transaction.
        with self.conn:
            self.conn.execute("UPDATE papers SET notes=? WHERE id=?", (notes, paper_id))
            self.conn.execute(
                "INSERT INTO paper_annotations(paper_id, channel, kind, content, recorded_at) "
                "VALUES (?, 'research_note', 'user', ?, ?)", (paper_id, notes, _now()),
            )

    def add_annotation(self, paper_id: int, content: str, *, kind: str = "user",
                       source_ref: str | None = None, origin_method: str = "declared",
                       evidence_key: str | None = None, commit: bool = True) -> sqlite3.Row:
        """Append provenance-labeled material without replacing personal notes."""
        if kind not in ANNOTATION_KINDS:
            raise ValueError("Unsupported annotation kind")
        if not isinstance(content, str) or not content.strip() or len(content) > 50_000:
            raise ValueError("Annotation must contain 1–50000 characters and cannot be blank")
        if source_ref is not None and (not isinstance(source_ref, str) or len(source_ref) > 2000):
            raise ValueError("Source reference must be at most 2000 characters")
        if self.get(paper_id) is None:
            raise KeyError(paper_id)
        with self.conn if commit else nullcontext():
            now = _now()
            cursor = self.conn.execute(
                "INSERT OR IGNORE INTO paper_annotations(paper_id, channel, kind, content, source_ref, "
                "recorded_at, origin_method, evidence_key) VALUES (?, 'annotation', ?, ?, ?, ?, ?, ?)",
                (paper_id, kind, content, (source_ref.strip() or None) if source_ref else None,
                 now, origin_method, evidence_key),
            )
            if cursor.rowcount:
                annotation_id = cursor.lastrowid
                self.conn.execute("INSERT INTO annotation_revisions(annotation_id, revision, content, review_status, recorded_at) VALUES (?, 1, ?, 'unreviewed', ?)",
                                  (annotation_id, content, now))
            else:
                annotation_id = self.conn.execute(
                    "SELECT id FROM paper_annotations WHERE paper_id=? AND evidence_key=?",
                    (paper_id, evidence_key),
                ).fetchone()[0]
        return self.conn.execute("SELECT * FROM paper_annotations WHERE id=?", (annotation_id,)).fetchone()

    def edit_annotation(self, paper_id: int, annotation_id: int, *, expected_revision: int,
                        content: str | None = None, review_status: str | None = None) -> sqlite3.Row:
        if content is not None and (not content.strip() or len(content) > 50_000):
            raise ValueError("Invalid annotation content")
        if review_status is not None and review_status not in {"unreviewed", "accepted", "dismissed"}:
            raise ValueError("Invalid review status")
        with self.conn:
            self.conn.execute("BEGIN IMMEDIATE")
            row = self.conn.execute("SELECT * FROM paper_annotations WHERE id=? AND paper_id=? "
                                    "AND channel='annotation'", (annotation_id, paper_id)).fetchone()
            if row is None:
                raise KeyError(annotation_id)
            if row["revision"] != expected_revision:
                raise ValueError("Annotation changed; reload before editing")
            if row["deleted_at"] is not None:
                raise ValueError("Annotation changed; restore it before editing")
            body = row["content"] if content is None else content
            status = row["review_status"] if review_status is None else review_status
            if (body, status) != (row["content"], row["review_status"]):
                now = _now()
                cursor = self.conn.execute(
                    "UPDATE paper_annotations SET content=?, review_status=?, updated_at=?, revision=revision+1 "
                    "WHERE id=? AND revision=?", (body, status, now, annotation_id, expected_revision),
                )
                if not cursor.rowcount:
                    raise ValueError("Annotation changed; reload before editing")
                self.conn.execute("INSERT INTO annotation_revisions(annotation_id, revision, content, review_status, recorded_at) VALUES (?, ?, ?, ?, ?)",
                                  (annotation_id, expected_revision + 1, body, status, now))
        return self.conn.execute("SELECT * FROM paper_annotations WHERE id=?", (annotation_id,)).fetchone()

    def list_annotations(self, paper_id: int, *, channel: str = "annotation", limit: int = 50,
                         before_id: int | None = None, deleted: bool = False) -> list[sqlite3.Row]:
        if channel not in {"annotation", "research_note"} or not 1 <= limit <= 201:
            raise ValueError("Invalid annotation channel or limit")
        if self.get(paper_id) is None:
            raise KeyError(paper_id)
        cursor_clause = " AND id<?" if before_id is not None else ""
        params = (paper_id, channel, before_id, limit) if before_id is not None else (paper_id, channel, limit)
        return self.conn.execute(
            f"SELECT * FROM paper_annotations WHERE paper_id=? AND channel=?{cursor_clause} "
            f"AND deleted_at IS {'NOT NULL' if deleted else 'NULL'} "
            "ORDER BY id DESC LIMIT ?", params,
        ).fetchall()

    def change_annotation_recovery(self, paper_id: int, annotation_id: int, *, expected_revision: int,
                                   delete: bool = False, restore_revision: int | None = None) -> sqlite3.Row:
        """Reversible deletion or append-only restoration, guarded against stale clients."""
        with self.conn:
            self.conn.execute("BEGIN IMMEDIATE")
            row = self.conn.execute("SELECT * FROM paper_annotations WHERE paper_id=? AND id=? "
                                    "AND channel='annotation'", (paper_id, annotation_id)).fetchone()
            if row is None:
                raise KeyError(annotation_id)
            if row['revision'] != expected_revision:
                raise ValueError("Annotation changed; reload before restoring or deleting")
            body, status = row['content'], row['review_status']
            if restore_revision is not None:
                old = self.conn.execute("SELECT * FROM annotation_revisions WHERE annotation_id=? AND revision=?",
                                        (annotation_id, restore_revision)).fetchone()
                if old is None:
                    raise KeyError(restore_revision)
                body, status = old['content'], old['review_status']
            now = _now()
            deleted_at = now if delete else None
            if not delete and restore_revision is None and row['deleted_at'] is None:
                return row
            if delete and row['deleted_at'] is not None:
                return row
            self.conn.execute("UPDATE paper_annotations SET content=?, review_status=?, deleted_at=?, "
                              "updated_at=?, revision=revision+1 WHERE id=?",
                              (body, status, deleted_at, now, annotation_id))
            self.conn.execute("INSERT INTO annotation_revisions(annotation_id, revision, content, review_status, recorded_at, deleted_at) "
                              "VALUES (?, ?, ?, ?, ?, ?)",
                              (annotation_id, expected_revision+1, body, status, now, deleted_at))
        return self.conn.execute("SELECT * FROM paper_annotations WHERE id=?", (annotation_id,)).fetchone()

    def annotation_history(self, paper_id: int, annotation_id: int, *, limit: int = 50,
                           before_revision: int | None = None) -> list[sqlite3.Row]:
        if not self.conn.execute("SELECT 1 FROM paper_annotations WHERE paper_id=? AND id=? AND channel='annotation'",
                                 (paper_id, annotation_id)).fetchone():
            raise KeyError(annotation_id)
        clause = ' AND revision<?' if before_revision is not None else ''
        params = (annotation_id, before_revision, limit) if before_revision is not None else (annotation_id, limit)
        return self.conn.execute(f"SELECT * FROM annotation_revisions WHERE annotation_id=?{clause} "
                                 "ORDER BY revision DESC LIMIT ?", params).fetchall()

    def restore_note(self, paper_id: int, revision_id: int, *, expected_note_id: int | None) -> sqlite3.Row:
        """Copy historical text into legacy papers.notes and append user restoration provenance."""
        with self.conn:
            self.conn.execute("BEGIN IMMEDIATE")
            paper = self.get(paper_id)
            old = self.conn.execute("SELECT * FROM paper_annotations WHERE paper_id=? AND id=? "
                                    "AND channel='research_note'", (paper_id, revision_id)).fetchone()
            if paper is None or old is None:
                raise KeyError(revision_id)
            current = self.conn.execute("SELECT id FROM paper_annotations WHERE paper_id=? AND channel='research_note' "
                                        "ORDER BY id DESC LIMIT 1", (paper_id,)).fetchone()
            if (current['id'] if current else None) != expected_note_id:
                raise ValueError("Research note changed; reload before restoring")
            if old['content'] != paper['notes']:
                self.conn.execute("UPDATE papers SET notes=? WHERE id=?", (old['content'], paper_id))
                self.conn.execute("INSERT INTO paper_annotations(paper_id, channel, kind, content, recorded_at, origin_method, source_ref) "
                                  "VALUES (?, 'research_note', 'user', ?, ?, 'history_restore', ?)",
                                  (paper_id, old['content'], _now(), f"Restored research-note revision #{revision_id}"))
        return self.get(paper_id)

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

    def record_research_run(
        self,
        *,
        job: str,
        started_at: str,
        completed_at: str,
        status: str,
        summary: dict[str, Any],
        error_message: str = "",
    ) -> int:
        with self.conn:
            cursor = self.conn.execute(
                "INSERT INTO research_runs(job, started_at, completed_at, status, summary_json, error_message) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (str(job), str(started_at), str(completed_at), str(status),
                 json.dumps(summary, ensure_ascii=False, default=str), str(error_message)[:2000]),
            )
            return int(cursor.lastrowid)

    def record_digest_delivery(
        self,
        *,
        channel: str,
        period: str,
        generated_at: str,
        sent_at: str | None,
        since_at: str,
        paper_ids: Iterable[int],
        output_path: str = "",
        status: str,
        error_message: str = "",
    ) -> int:
        with self.conn:
            normalized_ids = [int(value) for value in paper_ids]
            cursor = self.conn.execute(
                "INSERT INTO digest_deliveries(channel, period, generated_at, sent_at, since_at, paper_ids_json, output_path, status, error_message) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (str(channel), str(period), str(generated_at), sent_at, str(since_at),
                 json.dumps(normalized_ids), str(output_path), str(status), str(error_message)[:2000]),
            )
            delivery_id = int(cursor.lastrowid)
            if str(status) == "sent" and sent_at:
                self.conn.executemany(
                    "INSERT OR IGNORE INTO digest_delivery_papers(delivery_id, paper_id) VALUES (?, ?)",
                    [(delivery_id, paper_id) for paper_id in normalized_ids],
                )
            return delivery_id

    def first_digest_since_at(self, channel: str) -> str | None:
        row = self.conn.execute(
            "SELECT since_at FROM digest_deliveries WHERE channel=? AND status='sent' AND sent_at IS NOT NULL "
            "ORDER BY sent_at ASC, id ASC LIMIT 1",
            (str(channel),),
        ).fetchone()
        return str(row["since_at"]) if row else None

    def latest_digest_sent_at(self, channel: str) -> str | None:
        row = self.conn.execute(
            "SELECT sent_at FROM digest_deliveries WHERE channel=? AND status='sent' AND sent_at IS NOT NULL "
            "ORDER BY sent_at DESC, id DESC LIMIT 1",
            (str(channel),),
        ).fetchone()
        return str(row["sent_at"]) if row else None

    def stats(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT status, COUNT(*) AS n FROM papers GROUP BY status").fetchall()
        stats = {status: 0 for status in STATUSES}
        stats.update({str(row["status"]): int(row["n"]) for row in rows})
        stats["all"] = sum(stats.values())
        return stats
