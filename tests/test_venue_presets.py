import pytest

from sources.base import Paper
from storage.sqlite import PaperStore
from storage.venue_presets import ICONS, MAX_PRESETS, VenuePresetStore


def fields(**changes):
    return {'title': 'Контекст', 'icon': 'book', 'query': 'emotion context',
            'venue_query': 'Synthetic journal', **changes}


def test_seed_once_and_no_deleted_default_resurrection(tmp_path):
    path = tmp_path / 'synthetic.db'
    store = PaperStore(path)
    presets = VenuePresetStore(store)
    items = presets.list()
    assert len(items) == 3
    assert all(i['source_id'] is None and i['icon'] in ICONS for i in items)
    assert set(items[0]) == {'id', 'revision', 'title', 'icon', 'query', 'venue_query',
                            'source_id', 'year_from', 'year_to'}
    for item in items:
        presets.delete(item['id'], item['revision'])
    store.close()
    reopened = PaperStore(path)
    assert VenuePresetStore(reopened).list() == []
    assert reopened.conn.execute('SELECT COUNT(*) FROM research_venue_presets WHERE deleted=1').fetchone()[0] == 3
    reopened.close()


def test_create_partial_update_normalization_and_unicode(tmp_path):
    store = PaperStore(tmp_path / 'synthetic.db')
    presets = VenuePresetStore(store)
    item = presets.create(fields(source_id=' https://openalex.org/s123 ', year_from=2023, year_to=2026))
    assert item['source_id'] == 'S123'
    assert item['title'] == 'Контекст'
    updated = presets.update(item['id'], {'query': 'sarcasm', 'source_id': None}, item['revision'])
    assert updated['revision'] == 2
    assert updated['query'] == 'sarcasm' and updated['source_id'] is None
    assert updated['year_from'] == 2023 and updated['venue_query'] == item['venue_query']
    assert item != updated
    store.close()


def test_cross_connection_conflicts_and_missing_tombstones(tmp_path):
    path = tmp_path / 'synthetic.db'
    a = PaperStore(path)
    pa = VenuePresetStore(a)
    item = pa.list()[0]
    b = PaperStore(path)
    pb = VenuePresetStore(b)
    changed = pa.update(item['id'], {'title': 'Edited'}, item['revision'])
    with pytest.raises(ValueError, match='changed'):
        pb.update(item['id'], {'title': 'Stale'}, item['revision'])
    with pytest.raises(ValueError, match='changed'):
        pb.delete(item['id'], item['revision'])
    assert pb.list()[0]['title'] == 'Edited'
    pb.delete(changed['id'], changed['revision'])
    with pytest.raises(KeyError):
        pa.update(item['id'], {'title': 'Resurrect'}, changed['revision'])
    with pytest.raises(KeyError):
        pa.delete(item['id'], changed['revision'])
    with pytest.raises(KeyError):
        pa.update(999999, {'title': 'Missing'}, 1)
    a.close()
    b.close()


def test_active_count_bound_and_deleted_ids_not_reused(tmp_path):
    store = PaperStore(tmp_path / 'synthetic.db')
    presets = VenuePresetStore(store)
    for index in range(MAX_PRESETS - 3):
        presets.create(fields(title=f'Item {index}'))
    assert len(presets.list()) == MAX_PRESETS
    with pytest.raises(ValueError, match='20'):
        presets.create(fields())
    deleted = presets.list()[-1]
    presets.delete(deleted['id'], deleted['revision'])
    created = presets.create(fields())
    assert created['id'] > deleted['id']
    assert len(presets.list()) == MAX_PRESETS
    store.close()


@pytest.mark.parametrize('invalid', [
    {}, {'title': 'missing required fields'}, fields(extra='unsupported'),
    fields(title=''), fields(title='x' * 121), fields(query='x' * 501),
    fields(venue_query='x' * 201), fields(query='nul\x00value'),
    fields(icon='<script>'), fields(icon=['book']), fields(source_id=123),
    fields(source_id=''), fields(source_id='https://openalex.org/S1?filter=bad'),
    fields(source_id='https://example.invalid/S1'), fields(source_id='S1,S2'),
    fields(source_id='S' + '1' * 100), fields(year_from=True),
    fields(year_from='2023'), fields(year_to=999), fields(year_to=10000),
    fields(year_from=2026, year_to=2023),
])
def test_bounded_validation_rejects_invalid_presets(tmp_path, invalid):
    store = PaperStore(tmp_path / 'synthetic.db')
    presets = VenuePresetStore(store)
    before = presets.list()
    with pytest.raises(ValueError):
        presets.create(invalid)
    assert presets.list() == before
    store.close()


@pytest.mark.parametrize('revision', [0, -1, True, '1', None])
def test_revision_values_must_be_positive_integers(tmp_path, revision):
    store = PaperStore(tmp_path / 'synthetic.db')
    presets = VenuePresetStore(store)
    item = presets.list()[0]
    with pytest.raises(ValueError):
        presets.update(item['id'], {'title': 'Bad'}, revision)
    with pytest.raises(ValueError):
        presets.delete(item['id'], revision)
    store.close()


def test_partial_year_update_validates_merged_range(tmp_path):
    store = PaperStore(tmp_path / 'synthetic.db')
    presets = VenuePresetStore(store)
    item = presets.create(fields(year_from=2023, year_to=2026))
    with pytest.raises(ValueError, match='exceed'):
        presets.update(item['id'], {'year_from': 2027}, item['revision'])
    assert presets.list()[-1] == item
    store.close()


def test_additive_store_preserves_papers_and_enclosing_transaction(tmp_path):
    store = PaperStore(tmp_path / 'synthetic.db')
    paper_id = store.upsert_paper(Paper(source='fixture', title='Synthetic paper', authors=['A']),
                                  relevance_score=1.0, matched_groups={})
    store.set_notes(paper_id, 'Synthetic private notes')
    store.set_tags(paper_id, ['manual'])
    store.set_status(paper_id, 'read')
    before = dict(store.get(paper_id))
    presets = VenuePresetStore(store)
    presets.list()
    assert dict(store.get(paper_id)) == before
    store.conn.execute('BEGIN')
    item = presets.create(fields())
    presets.update(item['id'], {'title': 'Pending'}, item['revision'])
    assert store.conn.in_transaction
    store.conn.rollback()
    assert all(row['id'] != item['id'] for row in presets.list())
    assert dict(store.get(paper_id)) == before
    store.close()


def test_missing_seed_marker_never_replaces_existing_user_state(tmp_path):
    store = PaperStore(tmp_path / 'synthetic.db')
    presets = VenuePresetStore(store)
    items = presets.list()
    first = presets.update(items[0]['id'], {'title': 'Personal topic'}, items[0]['revision'])
    presets.delete(items[1]['id'], items[1]['revision'])
    with store.conn:
        store.conn.execute("DELETE FROM research_venue_preset_state WHERE name='seeded_v1'")
    reseeded = presets.list()
    assert len(reseeded) == 2 and reseeded[0] == first
    store.close()
