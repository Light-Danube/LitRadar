"""Bounded human-authored worksheets, independent of paper metadata and notes."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

FIELD_NAMES = (
    'task_scope', 'data_context', 'context_selection', 'method', 'baselines',
    'datasets', 'metrics', 'reported_outcome', 'author_limitations',
    'user_questions', 'evidence_granularity', 'verdict', 'reading_status',
    'rationale', 'gap_candidate', 'alternative_explanations', 'counterexample',
    'validation_experiment', 'venue_type', 'publication_status',
    'known_prior_art', 'what_differs', 'falsification', 'verification_needed',
)
ORIGINS = {'user', 'imported_metadata', 'abstract_review', 'full_text_review', 'unknown'}
ENUMS = {
    'evidence_granularity': {'metadata only', 'abstract reviewed', 'full text reviewed'},
    'verdict': {'', 'relevant', 'maybe', 'not relevant'},
    'venue_type': {'unknown', 'journal', 'conference/proceedings', 'repository/preprint', 'book series', 'hosting platform'},
    'publication_status': {'unverified', 'verified'},
}
MAX_FIELD_CHARS = 8000
MAX_WORKSHEET_BYTES = 100000
SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_worksheets (
    paper_id INTEGER PRIMARY KEY REFERENCES papers(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL CHECK(revision > 0),
    fields_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence_worksheet_revisions (
    paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    revision INTEGER NOT NULL,
    fields_json TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    PRIMARY KEY(paper_id, revision)
);
"""


def _defaults() -> dict[str, dict[str, str]]:
    values = {'evidence_granularity': 'metadata only', 'venue_type': 'unknown',
              'publication_status': 'unverified'}
    return {name: {'value': values.get(name, ''), 'origin': 'unknown',
                   'source_ref': '', 'location': '', 'reviewed_at': '',
                   'recorded_at': '', 'verification_status': 'unverified', 'source_type': ''}
            for name in FIELD_NAMES}


class EvidenceStore:
    """Initialize additive tables lazily on an existing PaperStore connection.

    Edits are partial field replacements with provenance objects. A field's origin
    describes human authorship/review, never an automatically inferred finding.
    """
    def __init__(self, store: Any) -> None:
        self.store = store
        self.conn = store.conn
        # Individual statements avoid executescript's implicit transaction commit.
        for statement in SCHEMA.split(';'):
            if statement.strip():
                self.conn.execute(statement)

    def get(self, paper_id: int) -> dict[str, Any]:
        if self.store.get(paper_id) is None:
            raise KeyError(paper_id)
        row = self.conn.execute('SELECT * FROM evidence_worksheets WHERE paper_id=?',
                                (paper_id,)).fetchone()
        fields = _defaults()
        if row:
            fields.update(json.loads(row['fields_json']))
        return {'paper_id': paper_id, 'revision': row['revision'] if row else 0,
                'updated_at': row['updated_at'] if row else None, 'fields': fields}

    def update(self, paper_id: int, fields: dict[str, Any], expected_revision: int = 0) -> dict[str, Any]:
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0:
            raise ValueError('Expected revision must be a nonnegative integer')
        if not isinstance(fields, dict) or not fields or fields.keys() - set(FIELD_NAMES):
            raise ValueError('Provide a nonempty mapping of supported evidence fields')
        now = datetime.now(timezone.utc).isoformat(timespec='seconds')
        clean = {}
        for name, statement in fields.items():
            if not isinstance(statement, dict) or statement.keys() - set(_defaults()[name]):
                raise ValueError(f'Invalid provenance object for {name}')
            if 'value' not in statement or statement.get('origin') not in ORIGINS:
                raise ValueError(f'{name} requires value and a supported origin')
            item = _defaults()[name] | statement
            if any(not isinstance(v, str) or len(v) > MAX_FIELD_CHARS or '\x00' in v for v in item.values()):
                raise ValueError(f'{name} values must be bounded text without NUL')
            if name in ENUMS and item['value'] not in ENUMS[name]:
                raise ValueError(f'Unsupported value for {name}')
            if item['verification_status'] not in {'unverified', 'verified'}:
                raise ValueError('Unsupported verification status')
            if (item['verification_status'] == 'verified' or name == 'publication_status' and item['value'] == 'verified') and not item['source_ref'].strip():
                raise ValueError('Verified statements require a source reference')
            if item['origin'] in {'imported_metadata', 'abstract_review', 'full_text_review'} and not item['source_ref'].strip():
                raise ValueError('Reviewed/imported statements require a source reference')
            item['recorded_at'] = now
            clean[name] = item
        with self.conn:
            self.conn.execute('BEGIN IMMEDIATE')
            current = self.get(paper_id)
            if current['revision'] != expected_revision:
                raise ValueError('Evidence changed; reload before editing')
            merged = current['fields'] | clean
            body = json.dumps(merged, ensure_ascii=False, sort_keys=True)
            if len(body.encode('utf-8')) > MAX_WORKSHEET_BYTES:
                raise ValueError('Evidence worksheet exceeds 100000 UTF-8 bytes')
            revision = expected_revision + 1
            self.conn.execute('INSERT INTO evidence_worksheets VALUES (?, ?, ?, ?) '
                              'ON CONFLICT(paper_id) DO UPDATE SET revision=excluded.revision, '
                              'fields_json=excluded.fields_json, updated_at=excluded.updated_at',
                              (paper_id, revision, body, now))
            self.conn.execute('INSERT INTO evidence_worksheet_revisions VALUES (?, ?, ?, ?)',
                              (paper_id, revision, body, now))
        return self.get(paper_id)
