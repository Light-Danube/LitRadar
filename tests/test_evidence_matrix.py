import csv
import io
import json

import pytest

from evidence_matrix import export_csv, export_markdown
from sources.base import Paper
from storage.evidence import EvidenceStore, MAX_FIELD_CHARS
from storage.sqlite import PaperStore


def make_paper(store, title='Synthetic контекст', doi='10.1000/synthetic'):
    return store.upsert_paper(Paper(source='synthetic', title=title, authors=['A. Example'],
                                   published_at='2024-01-01', venue='Test Proceedings',
                                   doi=doi, url='https://example.invalid/paper'),
                              relevance_score=2.0, matched_groups={})


def statement(value, **kwargs):
    return {'value': value, 'origin': 'user', **kwargs}


def test_additive_storage_preserves_personal_state_and_refresh(tmp_path):
    path = tmp_path / 'synthetic.db'
    store = PaperStore(path)
    paper_id = make_paper(store)
    store.set_notes(paper_id, 'PRIVATE synthetic note, never export')
    store.set_tags(paper_id, ['manual'])
    store.set_status(paper_id, 'read')
    before = dict(store.get(paper_id))
    evidence = EvidenceStore(store)
    initial = evidence.get(paper_id)
    assert initial['revision'] == 0
    assert initial['fields']['evidence_granularity']['value'] == 'metadata only'
    assert initial['fields']['publication_status']['value'] == 'unverified'
    assert dict(store.get(paper_id)) == before
    saved = evidence.update(paper_id, {'task_scope': statement('ERC'),
                                     'verdict': statement('relevant')})
    assert saved['revision'] == 1
    assert saved['fields']['task_scope']['recorded_at'].endswith('+00:00')
    make_paper(store)
    assert evidence.get(paper_id) == saved
    assert store.get(paper_id)['notes'] == before['notes']
    assert store.get(paper_id)['tags_json'] == before['tags_json']
    assert store.get(paper_id)['status'] == 'read'
    store.close()
    reopened = PaperStore(path)
    assert EvidenceStore(reopened).get(paper_id) == saved
    assert 'PRIVATE' not in export_markdown(reopened, [paper_id])
    assert 'PRIVATE' not in export_csv(reopened, [paper_id])
    reopened.close()


def test_partial_edit_revision_conflict_and_history(tmp_path):
    path = tmp_path / 'synthetic.db'
    a = PaperStore(path)
    paper_id = make_paper(a)
    ea = EvidenceStore(a)
    b = PaperStore(path)
    eb = EvidenceStore(b)
    ea.update(paper_id, {'method': statement('fixed window')})
    with pytest.raises(ValueError, match='reload'):
        eb.update(paper_id, {'method': statement('stale edit')}, expected_revision=0)
    changed = eb.update(paper_id, {'metrics': statement('not in abstract')}, expected_revision=1)
    assert changed['fields']['method']['value'] == 'fixed window'
    rows = a.conn.execute('SELECT * FROM evidence_worksheet_revisions ORDER BY revision').fetchall()
    assert [r['revision'] for r in rows] == [1, 2]
    assert json.loads(rows[0]['fields_json'])['metrics']['value'] == ''
    a.close()
    b.close()


@pytest.mark.parametrize('fields', [
    {}, {'made_up_field': statement('no')}, {'method': 'unattributed'},
    {'method': {'value': 'no origin'}},
    {'method': statement('x' * (MAX_FIELD_CHARS + 1))},
    {'method': statement('NUL\x00')},
    {'method': statement('invented', origin='llm')},
    {'method': statement('no attribution', origin='abstract_review')},
    {'method': statement('no attribution', verification_status='verified')},
    {'publication_status': statement('verified')},
    {'evidence_granularity': statement('guessed full paper')},
    {'venue_type': statement('ACM Digital Library')},
    {'method': statement('bad', location=123)},
])
def test_invalid_or_unattributed_evidence_is_atomic(tmp_path, fields):
    store = PaperStore(tmp_path / 'synthetic.db')
    paper_id = make_paper(store)
    evidence = EvidenceStore(store)
    with pytest.raises(ValueError):
        evidence.update(paper_id, fields)
    assert evidence.get(paper_id)['revision'] == 0
    store.close()


def test_reviewed_statements_keep_exact_attribution_and_bound_total_size(tmp_path):
    store = PaperStore(tmp_path / 'synthetic.db')
    paper_id = make_paper(store)
    evidence = EvidenceStore(store)
    evidence.update(paper_id, {'reported_outcome': statement(
        'Synthetic result only, comparator: baseline A', origin='full_text_review',
        source_ref='https://example.invalid/paper', source_type='PDF',
        location='Table 2, p. 4', reviewed_at='2026-10-14', verification_status='verified')})
    md = export_markdown(store, [paper_id])
    assert 'Table 2, p' in md
    assert 'https://example' in md
    with pytest.raises(ValueError, match='100000'):
        evidence.update(paper_id, {name: statement('文' * 7000) for name in
                                  ('method', 'baselines', 'datasets', 'metrics', 'data_context')},
                        expected_revision=1)
    assert evidence.get(paper_id)['revision'] == 1
    store.close()


def test_deterministic_utf8_markdown_and_csv_escape_hostile_metadata(tmp_path):
    store = PaperStore(tmp_path / 'synthetic.db')
    first = make_paper(store, title='<script>alert(1)</script> | [fake](javascript:evil) Контекст', doi='10.1000/a')
    second = make_paper(store, title='=HYPERLINK("https://example.invalid")', doi='10.1000/b')
    evidence = EvidenceStore(store)
    evidence.update(first, {'author_limitations': statement('<img src=x onerror=evil>\nA | B'),
                            'user_questions': statement('Could structure help?'),
                            'gap_candidate': statement('A candidate, no novelty established')})
    md = export_markdown(store, [second, first, first], research_question='<iframe>')
    assert md == export_markdown(store, [first, second], research_question='<iframe>')
    assert '<script>' not in md and '<img' not in md and '<iframe>' not in md
    assert '&lt;script&gt;' in md and '\\|' in md and '\\[fake\\]' in md
    assert 'Контекст' in md and '<br>' in md
    assert 'metadata only' in md and 'not verified' in md
    assert md.count('## Evidence card:') == 2
    assert 'Gap candidate status:** unverified' in md
    csv_text = export_csv(store, [second, first])
    assert csv_text == export_csv(store, [first, second, first])
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert rows[1]['title'].startswith("'=HYPERLINK")
    assert rows[0]['author_limitations.value'] == '<img src=x onerror=evil>\nA | B'
    assert rows[0]['user_questions.value'] == 'Could structure help?'
    assert rows[0]['author_limitations.origin'] == 'user'
    assert rows[0]['gap_candidate_status'] == 'unverified'
    store.close()


def test_missing_ids_and_export_bounds(tmp_path):
    store = PaperStore(tmp_path / 'synthetic.db')
    evidence = EvidenceStore(store)
    with pytest.raises(KeyError):
        evidence.get(999)
    with pytest.raises(KeyError):
        evidence.update(999, {'method': statement('none')})
    with pytest.raises(KeyError):
        export_markdown(store, [999])
    with pytest.raises(ValueError, match='200'):
        export_csv(store, range(1, 202))
    with pytest.raises(ValueError, match='positive integers'):
        export_csv(store, [True])
    assert 'not verified' in export_markdown(store, [])
    store.close()


def test_venue_observations_provenance_default_and_user_override(tmp_path):
    store = PaperStore(tmp_path / 'synthetic.db')
    paper_id = make_paper(store)
    venue = {'source_id': 'S1', 'display_name': 'Synthetic journal', 'venue_type': 'journal',
             'record_url': 'https://api.openalex.org/sources/S1', 'retrieved_at': '2026-10-14T00:00:00+00:00',
             'peer_review_status': 'unverified', 'scopus_status': 'unverified'}
    with store.conn:
        store.conn.execute('INSERT INTO discovery_venues VALUES (?, ?, ?)',
                           ('S1', json.dumps(venue), venue['retrieved_at']))
        store.conn.execute('INSERT INTO paper_venue_observations VALUES (?, ?, ?)',
                           (paper_id, 'S1', json.dumps({'venue': venue, 'original_venue': 'Synthetic journal',
                                                      'query': 'synthetic context', 'provider': 'openalex'})))
    rows = list(csv.DictReader(io.StringIO(export_csv(store, [paper_id]))))
    assert rows[0]['venue_type.value'] == 'journal'
    assert rows[0]['venue_type.origin'] == 'imported_metadata'
    assert rows[0]['publication_status.value'] == 'unverified'
    assert json.loads(rows[0]['venue_observations'])[0]['query'] == 'synthetic context'
    md = export_markdown(store, [paper_id])
    assert 'Synthetic journal' in md and 'S1' in md
    evidence = EvidenceStore(store)
    assert evidence.get(paper_id)['fields']['venue_type']['value'] == 'unknown'
    evidence.update(paper_id, {'venue_type': statement('conference/proceedings')})
    row = list(csv.DictReader(io.StringIO(export_csv(store, [paper_id]))))[0]
    assert row['venue_type.value'] == 'conference/proceedings'
    assert row['venue_type.origin'] == 'user'
    store.close()
