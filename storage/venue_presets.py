"""Local, user-editable research templates; a venue lead is not a source identity."""
from __future__ import annotations

from contextlib import contextmanager
import json
from typing import Any

from sources.venues import normalize_source_id

MAX_PRESETS = 20
ICONS = frozenset({'beacon', 'book', 'chat', 'spark', 'globe', 'layers'})
FIELDS = frozenset({'title', 'icon', 'query', 'venue_query', 'source_id', 'year_from', 'year_to'})
TEXT_LIMITS = {'title': 120, 'query': 500, 'venue_query': 200}
DEFAULT_PRESETS = (
    {'title': 'ERC context', 'icon': 'chat', 'query': 'emotion recognition conversation context',
     'venue_query': 'Computational Linguistics'},
    {'title': 'Sarcasm in discussion', 'icon': 'book', 'query': 'sarcasm conversation context',
     'venue_query': 'Transactions of the Association for Computational Linguistics'},
    {'title': 'Affective context', 'icon': 'spark', 'query': 'emotion recognition context selection',
     'venue_query': 'IEEE Transactions on Affective Computing'},
)
SCHEMA = (
    '''CREATE TABLE IF NOT EXISTS research_venue_presets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        revision INTEGER NOT NULL CHECK(revision > 0),
        fields_json TEXT NOT NULL,
        deleted INTEGER NOT NULL DEFAULT 0 CHECK(deleted IN (0, 1))
    )''',
    '''CREATE TABLE IF NOT EXISTS research_venue_preset_state (
        name TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )''',
)


def _revision(value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError('Expected revision must be a positive integer')


def _id(value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError('Preset ID must be a positive integer')


def _clean(fields: Any, current: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(fields, dict) or not fields or fields.keys() - FIELDS:
        raise ValueError('Provide a nonempty mapping of supported preset fields')
    item = {'icon': 'book', 'source_id': None, 'year_from': None, 'year_to': None}
    if current:
        item.update(current)
    item.update(fields)
    for name, maximum in TEXT_LIMITS.items():
        value = item.get(name)
        if not isinstance(value, str) or not value.strip() or len(value) > maximum or '\x00' in value:
            raise ValueError(f'{name} must contain 1–{maximum} characters without NUL')
        item[name] = value.strip()
    if not isinstance(item['icon'], str) or item['icon'] not in ICONS:
        raise ValueError('Choose a supported preset icon')
    source = item['source_id']
    if source is not None:
        if not isinstance(source, str) or not source.strip() or len(source) > 100:
            raise ValueError('source_id must be null or a bounded concrete OpenAlex source ID')
        item['source_id'] = normalize_source_id(source)
    for name in ('year_from', 'year_to'):
        value = item[name]
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or not 1000 <= value <= 9999):
            raise ValueError(f'{name} must be null or an integer between 1000 and 9999')
    if item['year_from'] is not None and item['year_to'] is not None and item['year_from'] > item['year_to']:
        raise ValueError('year_from must not exceed year_to')
    return item


class VenuePresetStore:
    """Additive storage on PaperStore.conn with optimistic edits and seed tombstones.

    No network, paper metadata or notes are touched. A stored source ID is only a
    saved selection; actual provider identity verification happens during search.
    """

    def __init__(self, store: Any) -> None:
        self.conn = store.conn
        for statement in SCHEMA:
            self.conn.execute(statement)

    @contextmanager
    def _write(self):
        # Acquire the SQLite writer before read/merge, while keeping any enclosing
        # caller transaction intact. A savepoint also rolls back validation errors.
        enclosing = self.conn.in_transaction
        if not enclosing:
            self.conn.execute('BEGIN IMMEDIATE')
        self.conn.execute('SAVEPOINT venue_presets_write')
        try:
            yield
            self.conn.execute('RELEASE venue_presets_write')
            if not enclosing:
                self.conn.commit()
        except BaseException:
            self.conn.execute('ROLLBACK TO venue_presets_write')
            self.conn.execute('RELEASE venue_presets_write')
            if not enclosing:
                self.conn.rollback()
            raise

    def _seed(self) -> None:
        with self._write():
            if self.conn.execute("SELECT 1 FROM research_venue_preset_state WHERE name='seeded_v1'").fetchone():
                return
            # Existing templates (including tombstones) count as prior user state.
            # A missing marker must never replace or resurrect them.
            if not self.conn.execute('SELECT 1 FROM research_venue_presets LIMIT 1').fetchone():
                for fields in DEFAULT_PRESETS:
                    self.conn.execute('INSERT INTO research_venue_presets(revision, fields_json) VALUES (1, ?)',
                                      (json.dumps(_clean(fields), ensure_ascii=False, sort_keys=True),))
            self.conn.execute("INSERT INTO research_venue_preset_state VALUES ('seeded_v1', '1')")

    @staticmethod
    def _item(row: Any) -> dict[str, Any]:
        return {'id': row['id'], 'revision': row['revision'], **json.loads(row['fields_json'])}

    def _get(self, ident: int) -> Any:
        row = self.conn.execute('SELECT * FROM research_venue_presets WHERE id=? AND deleted=0', (ident,)).fetchone()
        if row is None:
            raise KeyError(ident)
        return row

    def list(self) -> list[dict[str, Any]]:
        self._seed()
        return [self._item(row) for row in self.conn.execute(
            'SELECT * FROM research_venue_presets WHERE deleted=0 ORDER BY id').fetchall()]

    def create(self, fields: dict[str, Any]) -> dict[str, Any]:
        clean = _clean(fields)
        self._seed()
        with self._write():
            count = self.conn.execute('SELECT COUNT(*) FROM research_venue_presets WHERE deleted=0').fetchone()[0]
            if count >= MAX_PRESETS:
                raise ValueError('At most 20 active venue presets are allowed')
            cursor = self.conn.execute('INSERT INTO research_venue_presets(revision, fields_json) VALUES (1, ?)',
                                       (json.dumps(clean, ensure_ascii=False, sort_keys=True),))
            item = self._item(self._get(cursor.lastrowid))
        return item

    def update(self, ident: int, fields: dict[str, Any], expected_revision: int) -> dict[str, Any]:
        _id(ident)
        _revision(expected_revision)
        self._seed()
        with self._write():
            row = self._get(ident)
            if row['revision'] != expected_revision:
                raise ValueError('Preset changed; reload before editing')
            clean = _clean(fields, json.loads(row['fields_json']))
            self.conn.execute('UPDATE research_venue_presets SET fields_json=?, revision=revision+1 WHERE id=?',
                              (json.dumps(clean, ensure_ascii=False, sort_keys=True), ident))
            item = self._item(self._get(ident))
        return item

    def delete(self, ident: int, expected_revision: int) -> None:
        _id(ident)
        _revision(expected_revision)
        self._seed()
        with self._write():
            row = self._get(ident)
            if row['revision'] != expected_revision:
                raise ValueError('Preset changed; reload before deleting')
            self.conn.execute('UPDATE research_venue_presets SET deleted=1, revision=revision+1 WHERE id=?', (ident,))
