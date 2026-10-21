"""Offline language contracts: provider semantics, caches and durable user data."""
import json
import unicodedata

import pytest

from config import RadarConfig
from sources import cache, openalex, registry, venues
from sources.base import Paper
from sources.filters import normalize_metadata_language
from storage.sqlite import PaperStore


def work(language='uk'):
    return {'id': 'https://openalex.org/W1', 'display_name': 'Українські дослідження',
            'language': language, 'publication_year': 2025,
            'primary_location': {'source': {'id': 'https://openalex.org/S1', 'display_name': 'Журнал'}}}


def test_openalex_applies_server_filter_and_keeps_default_request(monkeypatch):
    calls = []
    monkeypatch.setattr(openalex, '_get_json', lambda url, params, **kw:
                        (calls.append(dict(params)) or {'results': [work()]}))
    papers = openalex.search('наукові дослідження', metadata_language='uk')
    assert calls[-1] == {'search': 'наукові дослідження', 'per-page': 25, 'filter': 'language:uk'}
    assert papers[0].metadata_language == 'uk'
    assert papers[0].raw['language'] == 'uk'
    assert papers[0].language_basis == 'openalex_detected_title_abstract'
    openalex.search('наукові дослідження')
    assert calls[-1] == {'search': 'наукові дослідження', 'per-page': 25}


@pytest.mark.parametrize('value', [None, '', 'und', 'ukr', 'unknown', 'zz', 'xx', 123])
def test_unknown_is_not_inferred_from_ukrainian_title(value):
    paper = openalex._work_to_paper(work(value))
    assert paper.metadata_language is None
    assert paper.raw['language'] == value


@pytest.mark.parametrize('value', ['en', None, 'und'])
def test_filtered_response_contradiction_is_an_error_not_silent_postfilter(monkeypatch, value):
    monkeypatch.setattr(openalex, '_get_json', lambda *a, **kw: {'results': [work(value)]})
    with pytest.raises(ValueError, match='contradicts'):
        openalex.search('дослідження', metadata_language='uk')


@pytest.mark.parametrize('value', ['publication:uk', 'ua', None, True, ['uk']])
def test_invalid_language_rejected(value):
    with pytest.raises(ValueError):
        normalize_metadata_language(value)


def test_unsupported_mixed_search_rejects_before_cache_network_or_database(tmp_path, monkeypatch):
    monkeypatch.setattr(registry, 'load_cached', lambda *a, **kw: pytest.fail('cache read'))
    monkeypatch.setattr(openalex, '_get_json', lambda *a, **kw: pytest.fail('network'))
    with pytest.raises(ValueError, match='unsupported for: semantic_scholar, arxiv'):
        registry.search_all_sources('Україна', metadata_language='uk', config=RadarConfig())
    from pipeline import search_and_ingest
    db = tmp_path/'absent.sqlite'
    profile = tmp_path/'profile.json'
    profile.write_text('{"groups": []}', encoding='utf-8')
    with pytest.raises(ValueError, match='unsupported'):
        search_and_ingest('Україна', db_path=db, profile_path=profile, metadata_language='uk')
    assert not db.exists()


def test_filtered_registry_cache_and_legacy_cache_do_not_mix(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(registry, 'load_cached', lambda s,q,n,ttl,**kw: cache.load_cached(s,q,n,ttl,tmp_path,**kw))
    monkeypatch.setattr(registry, 'save_cached', lambda s,q,n,p,**kw: cache.save_cached(s,q,n,p,tmp_path,**kw))
    def search(q, n, c, language='any'):
        calls.append(language)
        return [openalex._work_to_paper(work(language if language != 'any' else None))]
    selected = registry.SourceRegistry([registry.SourceDefinition('openalex', search, search)])
    config = RadarConfig(enabled_sources=('openalex',), source_cache_ttl=3600)
    for language in ['any', 'uk', 'en', 'uk', 'any']:
        _, errors = registry.search_all_sources('Україна', registry=selected, config=config,
                                               metadata_language=language)
        assert errors == {}
    assert calls == ['any', 'uk', 'en']
    assert len(list(tmp_path.rglob('*.json'))) == 3
    assert cache.cache_path('openalex', 'x|metadata-language:uk', 20, tmp_path) != cache.cache_path(
        'openalex', 'x', 20, tmp_path, metadata_language='uk')
    # Old caches without new Paper fields stay readable.
    path = cache.cache_path('old', 'query', 20, tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'papers': [{'source': 'old', 'title': 'Стара праця'}]}))
    assert cache.load_cached('old', 'query', 20, 3600, tmp_path)[0].metadata_language is None


def test_venue_filters_and_snapshot_provenance(monkeypatch):
    calls = []
    def fetch(url, params, **kwargs):
        calls.append(params)
        if url.endswith('/sources/S1'):
            return {'id': 'https://openalex.org/S1', 'display_name': 'Журнал'}
        return {'meta': {'count': 1}, 'results': [work()]}
    monkeypatch.setattr(openalex, '_get_json', fetch)
    result = venues.search_venue('дослідження', 'S1', metadata_language='uk', year_from=2023)
    assert calls[-1]['filter'] == 'primary_location.source.id:S1,language:uk,publication_year:2023-9999'
    assert result.provenance['query'] == 'дослідження'
    assert result.provenance['metadata_language'] == 'uk'
    assert result.to_dict()['papers'][0]['raw']['language'] == 'uk'


def test_venue_language_cache_and_user_histories(tmp_path, monkeypatch):
    import venue_discovery
    calls = []
    def fetch(url, params, **kwargs):
        if url.endswith('/sources/S1'):
            return {'id': 'https://openalex.org/S1', 'display_name': 'Журнал'}
        calls.append(params)
        language = 'en' if 'language:en' in params['filter'] else 'uk'
        return {'meta': {'count': 1}, 'results': [work(language)]}
    monkeypatch.setattr(openalex, '_get_json', fetch)
    store = PaperStore(tmp_path/'synthetic.sqlite')
    try:
        pid = store.upsert_paper(Paper(source='fixture', title=work()['display_name']), relevance_score=.7, matched_groups={})
        store.set_notes(pid, 'Мої нотатки')
        store.set_tags(pid, ['моє'])
        store.set_status(pid, 'read')
        annotation = store.add_annotation(pid, 'Збережена анотація')
        for language in ['any', 'uk', 'en', 'uk']:
            result = venue_discovery.search_and_store(store, 'дослідження', 'S1', metadata_language=language)
            assert result['paper_ids'] == [pid]
        assert len(calls) == 3
        assert result['cache_hit']
        row = store.get(pid)
        assert (row['notes'], json.loads(row['tags_json']), row['status']) == ('Мої нотатки', ['моє'], 'read')
        assert store.list_annotations(pid)[0]['id'] == annotation['id']
        refs = json.loads(row['source_refs_json'])
        assert refs['openalex']['metadata_language_raw'] == 'uk'
        assert refs['openalex']['language_basis'] == 'openalex_detected_title_abstract'
    finally:
        store.close()


def test_ukrainian_profile_casefold_and_canonical_unicode():
    from ranking.keywords import KeywordGroup, KeywordProfile
    profile = KeywordProfile([KeywordGroup('uk', 1, ('українські', 'дослідження', 'emotion'))])
    assert profile.match(unicodedata.normalize('NFD', 'УКРАЇНСЬКІ дослідження Emotion')) == {
        'uk': ['українські', 'дослідження', 'emotion']}
    assert profile.match('эмоция') == {}


def test_cli_language_is_explicit_and_default_unchanged(capsys, tmp_path):
    from cli import build_parser, cmd_search
    parser = build_parser()
    assert parser.parse_args(['search', 'Україна']).metadata_language == 'any'
    args = parser.parse_args(['--db', str(tmp_path/'absent.sqlite'), 'search', 'Україна', '--metadata-language', 'uk'])
    assert cmd_search(args) == 2
    assert 'unsupported' in capsys.readouterr().err
    assert not (tmp_path/'absent.sqlite').exists()


def test_web_language_validation_and_forwarding(tmp_path, monkeypatch):
    pytest.importorskip('fastapi', reason='optional browser workspace dependency')
    pytest.importorskip('httpx', reason='optional browser workspace test dependency')
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from web.research_api import register_research_routes
    import web.research_api as api
    app = FastAPI()
    register_research_routes(app, tmp_path/'test.sqlite', tmp_path/'results')
    calls = []
    monkeypatch.setattr(api.RadarConfig, 'load', classmethod(lambda cls: RadarConfig()))
    monkeypatch.setattr(api.venue_discovery, 'search_and_store', lambda *a, **kw:
                        (calls.append(kw) or {'status': 'zero_results', 'papers': [], 'paper_ids': []}))
    client = TestClient(app)
    base = {'query': 'Україна', 'source_id': 'S1'}
    assert client.post('/api/research/search', json=dict(base, metadata_language='ua')).status_code == 422
    assert calls == []
    assert client.post('/api/research/search', json=dict(base, metadata_language='uk')).status_code == 200
    assert calls[-1]['metadata_language'] == 'uk'
    assert client.post('/api/research/search', json=base).status_code == 200
    assert 'metadata_language' not in calls[-1]


def test_example_profile_is_opt_in_and_matches_both_languages():
    from pathlib import Path
    from ranking.keywords import KeywordProfile
    root = Path(__file__).resolve().parents[1]
    profile = KeywordProfile.from_json(root/'research_profile.uk-en.example.json')
    assert profile.match('Виявлення сарказму та emotion recognition')
    original = KeywordProfile.from_json(root/'research_profile.json')
    assert original.semantic_weight == .65


def test_ukrainian_saved_library_search_uses_unicode_fts(tmp_path):
    store = PaperStore(tmp_path/'unicode.sqlite')
    try:
        if not store.fts_available:
            pytest.skip('SQLite build has no FTS5; Cyrillic LIKE equivalence is not promised')
        pid = store.upsert_paper(Paper(source='fixture', title='Українські дослідження'), relevance_score=0, matched_groups={})
        assert [r['id'] for r in store.list_papers(query='УКРАЇНСЬКІ')] == [pid]
    finally:
        store.close()


def test_legacy_cache_replay_retains_openalex_language_provenance(tmp_path):
    from dataclasses import asdict
    from sources.filters import paper_from_cache
    fresh = openalex._work_to_paper(work())
    legacy = asdict(fresh)
    del legacy['metadata_language'], legacy['language_basis']
    path = cache.cache_path('openalex', 'Україна', 20, tmp_path/'cache')
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'papers': [legacy]}), encoding='utf-8')
    restored = cache.load_cached('openalex', 'Україна', 20, 3600, tmp_path/'cache')[0]
    assert restored.metadata_language == 'uk'
    assert paper_from_cache(legacy).language_basis == fresh.language_basis
    store = PaperStore(tmp_path/'legacy-cache.sqlite')
    try:
        pid = store.upsert_paper(fresh, relevance_score=0, matched_groups={})
        store.upsert_paper(restored, relevance_score=0, matched_groups={})
        refs = json.loads(store.get(pid)['source_refs_json'])['openalex']
        assert refs['metadata_language'] == refs['metadata_language_raw'] == 'uk'
        assert refs['language_basis'] == fresh.language_basis
    finally:
        store.close()


def test_legacy_venue_cache_discloses_language_without_a_request(tmp_path, monkeypatch):
    import venue_discovery
    def fetch(url, params, **kwargs):
        if url.endswith('/sources/S1'):
            return {'id': 'https://openalex.org/S1', 'display_name': 'Журнал'}
        return {'meta': {'count': 1}, 'results': [work()]}
    monkeypatch.setattr(openalex, '_get_json', fetch)
    store = PaperStore(tmp_path/'venue-cache.sqlite')
    try:
        venue_discovery.search_and_store(store, 'дослідження', 'S1')
        row = store.conn.execute('SELECT cache_key,payload_json FROM venue_search_cache').fetchone()
        payload = json.loads(row['payload_json'])
        for paper in payload['papers']:
            del paper['metadata_language'], paper['language_basis']
        store.conn.execute('UPDATE venue_search_cache SET payload_json=? WHERE cache_key=?',
                           (json.dumps(payload), row['cache_key']))
        store.conn.commit()
        monkeypatch.setattr(openalex, '_get_json', lambda *a, **kw: pytest.fail('legacy cache made request'))
        result = venue_discovery.search_and_store(store, 'дослідження', 'S1')
        assert result['cache_hit']
        assert result['papers'][0]['metadata_language'] == 'uk'
        assert result['papers'][0]['language_basis'] == 'openalex_detected_title_abstract'
    finally:
        store.close()
