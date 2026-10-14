"""Exercise real CLI/API/discovery adapters with only HTTP transport replaced."""
from io import BytesIO
import json
import urllib.error
import urllib.parse

import pytest

from cli import build_parser
from config import RadarConfig
from sources.base import Paper
from storage.evidence import EvidenceStore
from storage.sqlite import PaperStore


def source(identity='S1'):
    return {'id': f'https://openalex.org/{identity}', 'display_name': 'Synthetic collision journal',
            'type': 'journal', 'issn_l': '1234-5678' if identity == 'S1' else '8765-4321',
            'issn': [], 'host_organization_name': 'Synthetic publisher'}


def work():
    return {'id': 'https://openalex.org/W1', 'display_name': 'Synthetic context',
            'doi': 'https://doi.org/10.1234/synthetic', 'publication_year': 2024,
            'publication_date': '2024-02-01', 'primary_location': {'source': source()}}


@pytest.fixture
def library(tmp_path, monkeypatch):
    monkeypatch.setattr(RadarConfig, 'load', lambda: RadarConfig(
        source_retries=0, source_timeout=1, source_cache_ttl=3600))
    db = tmp_path / 'synthetic.sqlite3'
    store = PaperStore(db)
    pid = store.upsert_paper(Paper(source='fixture', title='Synthetic context',
                                 doi='10.1234/synthetic'), relevance_score=.8, matched_groups={})
    store.set_notes(pid, 'Синтетична нотатка')
    store.set_tags(pid, ['manual'])
    store.set_status(pid, 'read')
    EvidenceStore(store).update(pid, {'method': {'value': 'Human reviewed', 'origin': 'user'}}, 0)
    store.close()
    return db, pid, tmp_path / 'research'


def transport(monkeypatch, *, failure_stage=None, error=None, contaminated=False, expected_timeout=1):
    calls = []

    def urlopen(request, timeout):
        parsed = urllib.parse.urlparse(request.full_url)
        params = urllib.parse.parse_qs(parsed.query)
        assert parsed.netloc == 'api.openalex.org'
        assert timeout == expected_timeout
        stage = 'lookup' if parsed.path == '/sources' else 'source' if parsed.path == '/sources/S1' else 'works'
        calls.append((stage, params))
        if stage == failure_stage:
            raise error
        if stage == 'lookup':
            payload = {'results': [source(), source('S2')]}
        elif stage == 'source':
            payload = source()
        else:
            assert parsed.path == '/works'
            assert params['filter'] == ['primary_location.source.id:S1,publication_year:2023-2026']
            assert params['per-page'] == ['5'] and params['page'] == ['1']
            item = work()
            if contaminated:
                item['primary_location']['source'] = source('S2')
            payload = {'results': [item], 'meta': {'count': 1}}
        return BytesIO(json.dumps(payload).encode('utf-8'))

    monkeypatch.setattr('urllib.request.urlopen', urlopen)
    return calls


def state(db):
    store = PaperStore(db)
    try:
        return {table: [tuple(row) for row in store.conn.execute(f'SELECT * FROM {table} ORDER BY 1')]
                for table in ('papers', 'paper_annotations', 'annotation_revisions',
                              'evidence_worksheets', 'evidence_worksheet_revisions',
                              'paper_identifiers', 'discovery_venues', 'paper_venue_observations',
                              'venue_search_cache')}
    finally:
        store.close()


def test_cli_lookup_to_browser_search_cache_and_evidence(library, monkeypatch, capsys):
    pytest.importorskip('fastapi', reason='optional browser workspace dependency')
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from web.research_api import register_research_routes
    db, pid, root = library
    calls = transport(monkeypatch)
    parser = build_parser()
    args = parser.parse_args(['--db', str(db), 'venue', 'lookup', 'Collision', '--limit', '3'])
    assert args.func(args) == 0
    found = json.loads(capsys.readouterr().out)
    assert found['status'] == 'ambiguous_venue'
    assert [v['source_id'] for v in found['venues']] == ['S1', 'S2']
    assert found['venues'][0]['issn_l'] != found['venues'][1]['issn_l']
    assert all(v['peer_review_status'] == v['scopus_status'] == v['wos_status'] == 'unverified'
               for v in found['venues'])
    query = 'context & emotion/українська'
    app = FastAPI()
    register_research_routes(app, db, root)
    with TestClient(app) as client:
        # Local views and worksheet reads do not implicitly invoke the provider.
        assert client.get('/api/research/artifacts').status_code == 200
        assert client.get(f'/api/papers/{pid}/evidence').status_code == 200
        assert len(calls) == 1
        payload = {'source_id': 'S1', 'query': query, 'year_from': 2023, 'year_to': 2026, 'limit': 5}
        first = client.post('/api/research/search', json=payload)
        second = client.post('/api/research/search', json=payload)
        assert first.status_code == second.status_code == 200
        assert first.json()['paper_ids'] == second.json()['paper_ids'] == [pid]
        assert first.json()['newly_stored'] == 0 and second.json()['cache_hit'] is True
        assert calls[-1][1]['search'] == [query] and len(calls) == 3
        assert first.json()['artifact']['identifier'] != second.json()['artifact']['identifier']
        evidence = client.get(f'/api/papers/{pid}/evidence').json()
        assert evidence['revision'] == 1 and evidence['fields']['method']['value'] == 'Human reviewed'
    store = PaperStore(db)
    assert (store.get(pid)['notes'], store.get(pid)['status'], json.loads(store.get(pid)['tags_json'])) == (
        'Синтетична нотатка', 'read', ['manual'])
    assert store.get(pid)['relevance_score'] == .8
    store.close()
    # CLI shares the same cache and emits an implemented browser handoff.
    args = parser.parse_args(['--db', str(db), 'venue', 'search', 'S1', query,
                              '--year-from', '2023', '--year-to', '2026', '--limit', '5'])
    assert args.func(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['cache_hit'] is True and len(calls) == 3
    assert 'Research' in result['browser_handoff'] and 'planned' not in result['browser_handoff']
    assert len(list(root.iterdir())) == 3


@pytest.mark.parametrize('stage', ['lookup', 'source', 'works'])
@pytest.mark.parametrize('error,status', [
    (urllib.error.HTTPError('https://example.invalid/?api_key=SECRET', 429, 'SECRET', {}, None), 'rate_limited'),
    (urllib.error.HTTPError('https://example.invalid/?api_key=SECRET', 503, 'SECRET', {}, None), 'provider_error'),
    (TimeoutError('SECRET'), 'timeout'),
    (urllib.error.URLError('SECRET'), 'network_unavailable'),
])
def test_provider_transport_failures_preserve_library(library, monkeypatch, stage, error, status):
    pytest.importorskip('fastapi', reason='optional browser workspace dependency')
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from web.research_api import register_research_routes
    db, _, root = library
    before = state(db)
    transport(monkeypatch, failure_stage=stage, error=error)
    app = FastAPI()
    register_research_routes(app, db, root)
    with TestClient(app) as client:
        response = client.post('/api/research/venues/lookup', json={'query': 'Collision'}) if stage == 'lookup' else client.post(
            '/api/research/search', json={'source_id': 'S1', 'query': 'context',
                                         'year_from': 2023, 'year_to': 2026, 'limit': 5})
    assert response.status_code == 502 and response.json()['detail']['status'] == status
    assert 'SECRET' not in response.text
    assert state(db) == before
    assert not root.exists() or list(root.iterdir()) == []


def test_contaminated_provider_page_rejected_atomically(library, monkeypatch):
    db, _, root = library
    from venue_discovery import search_and_store
    from sources.venues import VenueMetadataError
    before = state(db)
    transport(monkeypatch, contaminated=True)
    store = PaperStore(db)
    with pytest.raises(VenueMetadataError, match='selected venue'):
        search_and_store(store, 'context', 'S1', year_from=2023, year_to=2026, limit=5,
                         config=RadarConfig(source_timeout=1, source_retries=0))
    store.close()
    assert state(db) == before and not root.exists()


def test_live_probe_requires_explicit_request_and_source_choice(monkeypatch, capsys):
    from scripts.venue_provider_probe import main
    monkeypatch.setattr('urllib.request.urlopen', lambda *a, **k: pytest.fail('implicit request'))
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
    capsys.readouterr()
    monkeypatch.setattr('sources.venues.lookup_venues', lambda *a, **k: [])
    monkeypatch.setattr('sources.venues.search_venue', lambda *a, **k: pytest.fail('unselected source searched'))
    assert main(['--live', '--source-id', 'S1']) == 1
    output = json.loads(capsys.readouterr().out)
    assert output['status'] == 'invalid_request' and output['live_search_verified'] is False


def test_live_probe_classifies_proxy_failure_without_exception_leak(monkeypatch, capsys):
    from scripts.venue_provider_probe import main
    def fail(*a, **k):
        raise urllib.error.URLError('Tunnel connection failed: 403 Forbidden; api_key=SECRET')
    monkeypatch.setattr('sources.venues.lookup_venues', fail)
    assert main(['--live']) == 1
    raw = capsys.readouterr().out
    output = json.loads(raw)
    assert output['environment_limitation'] == 'proxy_tunnel_http_403'
    assert output['live_search_verified'] is False and 'SECRET' not in raw


def test_probe_uses_public_transport_without_config_or_library(monkeypatch, capsys):
    from scripts.venue_provider_probe import main
    monkeypatch.setattr(RadarConfig, 'load', lambda: pytest.fail('personal config accessed'))
    monkeypatch.setattr(PaperStore, '__init__', lambda *a, **k: pytest.fail('library accessed'))
    calls = transport(monkeypatch, expected_timeout=8)
    assert main(['--live', '--source-id', 'S1']) == 0
    output = json.loads(capsys.readouterr().out)
    assert output['selected_source'] == 'S1' and output['work_ids'] == ['https://openalex.org/W1']
    assert output['provenance']['filter'] == 'primary_location.source.id:S1,publication_year:2023-2026'
    assert output['no_database_access'] is True and len(calls) == 3
