import json
import urllib.error
import pytest
pytest.importorskip('fastapi', reason='optional browser workspace dependency')
pytest.importorskip('httpx', reason='optional browser workspace test dependency')
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sources.base import Paper
from sources.venues import Venue
from storage.sqlite import PaperStore
from web.research_api import register_research_routes


@pytest.fixture
def workspace(tmp_path):
    db=tmp_path/'synthetic.sqlite3'
    store=PaperStore(db)
    paper_id=store.upsert_paper(Paper(source='openalex',title='Synthetic context',doi='10.1234/context'),relevance_score=0,matched_groups={})
    store.conn.execute('UPDATE papers SET notes=? WHERE id=?',('Personal test note',paper_id));store.conn.commit();store.close()
    app=FastAPI();register_research_routes(app,db,tmp_path/'research')
    return TestClient(app),paper_id,db,tmp_path/'research'


def search_result():
    return {'status':'zero_results','paper_ids':[],'papers':[],'cache_hit':True,'newly_stored':0,'count':0,'truncated':False}


def test_explicit_lookup_and_empty_search_saved(monkeypatch,workspace):
    client,_,_,root=workspace;calls=[]
    monkeypatch.setattr('web.research_api.RadarConfig.load',lambda:object())
    venue=Venue('S1','Test','journal',None,(),None,'https://api.openalex.org/sources/S1','2026-10-14T00:00:00+00:00')
    monkeypatch.setattr('web.research_api.venue_discovery.lookup',lambda *a,**k:[venue])
    monkeypatch.setattr('web.research_api.venue_discovery.search_and_store',lambda *a,**k:(calls.append(k) or search_result()))
    assert client.get('/api/research/artifacts').json()=={'items':[]}
    response=client.post('/api/research/venues/lookup',json={'query':'Test'})
    assert response.status_code==200 and response.json()['venues'][0]['source_id']=='S1'
    response=client.post('/api/research/search',json={'source_id':'S1','query':'context','identifier':'empty-page'})
    assert response.status_code==200
    result=response.json();assert result['artifact']['identifier']=='empty-page'
    assert result['status']=='zero_results' and calls[0]['force'] is False
    assert json.loads((root/'empty-page'/'search.json').read_text())['paper_ids']==[]
    assert len(client.get('/api/research/artifacts').json()['items'])==1
    assert client.get('/api/research/artifacts/empty-page/search.json').status_code==200
    assert client.get('/api/research/artifacts/empty-page/private.txt').status_code==422


def test_identifier_collision_precedes_config_provider_ingestion(monkeypatch,workspace):
    client,_,_,root=workspace;root.mkdir();(root/'exists').mkdir()
    monkeypatch.setattr('web.research_api.RadarConfig.load',lambda:pytest.fail('config loaded before reservation'))
    for identifier,status in [('exists',409),('../escape',422),('CON',422),('com1',422),('LPT9',422)]:
        response=client.post('/api/research/search',json={'source_id':'S1','query':'context','identifier':identifier})
        assert response.status_code==status


@pytest.mark.parametrize('fields',[{'page':11},{'limit':True},{'refresh':'yes'},{'year_from':999},{'query':'a'*501},{'source_id':'a journal'},{'source_id':'S'+'1'*100}])
def test_invalid_search_inputs_precede_network(monkeypatch,workspace,fields):
    client,*_=workspace
    monkeypatch.setattr('web.research_api.RadarConfig.load',lambda:pytest.fail('invalid input loaded config'))
    assert client.post('/api/research/search',json={'query':'context','source_id':'S1',**fields}).status_code==422


@pytest.mark.parametrize('error,status',[ (urllib.error.HTTPError('https://secret.example?api_key=secret',429,'denied',{},None),'rate_limited'),(TimeoutError('secret'),'timeout')])
def test_provider_safe_errors(monkeypatch,workspace,error,status):
    client,*_=workspace
    monkeypatch.setattr('web.research_api.RadarConfig.load',lambda:object())
    def fail(*a,**k):raise error
    monkeypatch.setattr('web.research_api.venue_discovery.lookup',fail)
    response=client.post('/api/research/venues/lookup',json={'query':'context'})
    assert response.status_code==502 and response.json()['detail']['status']==status
    assert 'secret' not in response.text


def test_evidence_revision_snapshot_export_preserves_notes(workspace):
    client,paper_id,db,root=workspace
    uri=f'/api/papers/{paper_id}/evidence'
    assert client.get(uri).json()['revision']==0
    payload={'fields':{'task_scope':{'value':'ERC','origin':'user'}},'expected_revision':0}
    response=client.patch(uri,json=payload)
    assert response.status_code==200 and response.json()['revision']==1
    assert 'evidence.json' in response.json()['artifact']['files']
    assert client.patch(uri,json=payload).status_code==409
    assert client.get('/api/papers/99999/evidence').status_code==404
    export=client.post('/api/research/exports',json={'paper_ids':[paper_id],'identifier':'matrix','research_question':'Context?'})
    assert export.status_code==200
    assert set(export.json()['files'])=={'manifest.json','matrix.md','matrix.csv'}
    content=client.get('/api/research/artifacts/matrix/matrix.md').text
    assert 'ERC' in content and 'Personal test note' not in content
    store=PaperStore(db);assert store.get(paper_id)['notes']=='Personal test note';store.close()


def test_persistence_failure_discloses_db_success(monkeypatch,workspace):
    client,paper_id,db,_=workspace
    monkeypatch.setattr('web.research_files._Reservation.save',lambda *a,**k:(_ for _ in ()).throw(OSError('secret path')))
    response=client.patch(f'/api/papers/{paper_id}/evidence',json={'fields':{'task_scope':{'value':'ERC','origin':'user'}},'expected_revision':0})
    assert response.status_code==503 and response.json()['detail']['saved_in_database'] is True
    assert 'secret' not in response.text
    assert client.get(f'/api/papers/{paper_id}/evidence').json()['revision']==1


def test_bounded_body_and_export_ids(workspace):
    client,*_=workspace
    assert client.post('/api/research/exports',content='a'*150001).status_code==413
    for payload in ({'paper_ids':[]},{'paper_ids':[True]},{'paper_ids':list(range(1,102))},{'paper_ids':[99999]}):
        assert client.post('/api/research/exports',json=payload).status_code in (422,404)


def test_preset_routes_without_online_configuration(monkeypatch,workspace):
    client,*_=workspace
    monkeypatch.setattr('web.research_api.RadarConfig.load',lambda:pytest.fail('preset requested network config'))
    initial=client.get('/api/research/presets');assert initial.status_code==200 and len(initial.json()['items'])==3
    response=client.post('/api/research/presets',json={'title':'My topic','query':'sarcasm','venue_query':'Computational Linguistics','icon':'chat'})
    assert response.status_code==200
    item=response.json();uri=f"/api/research/presets/{item['id']}"
    assert client.put(uri,json={'fields':{'title':'Updated'},'expected_revision':item['revision']}).status_code==200
    assert client.put(uri,json={'fields':{'title':'Stale'},'expected_revision':item['revision']}).status_code==409
    assert client.delete(uri,params={'expected_revision':item['revision']+1}).json()=={'ok':True}


def test_multiple_lookup_candidates_report_ambiguity(monkeypatch,workspace):
    client,*_=workspace
    monkeypatch.setattr('web.research_api.RadarConfig.load',lambda:object())
    records=[Venue(f'S{index}','Same','journal',None,(),None,'https://api.openalex.org/sources','2026-10-14T00:00:00+00:00') for index in (1,2)]
    monkeypatch.setattr('web.research_api.venue_discovery.lookup',lambda *a,**k:records)
    response=client.post('/api/research/venues/lookup',json={'query':'Same'})
    assert response.status_code==200 and response.json()['status']=='ambiguous_venue'
    assert len(response.json()['venues'])==2


def test_network_oserror_distinct_from_artifact_failure(monkeypatch,workspace):
    client,*_=workspace
    monkeypatch.setattr('web.research_api.RadarConfig.load',lambda:object())
    monkeypatch.setattr('web.research_api.venue_discovery.lookup',lambda *a,**k:(_ for _ in ()).throw(OSError('secret URL')))
    response=client.post('/api/research/venues/lookup',json={'query':'context'})
    assert response.status_code==502 and response.json()['detail']['status']=='network_unavailable'
    assert 'secret' not in response.text


def test_search_snapshot_failure_explicit_db_state(monkeypatch,workspace):
    client,*_=workspace
    monkeypatch.setattr('web.research_api.RadarConfig.load',lambda:object())
    monkeypatch.setattr('web.research_api.venue_discovery.search_and_store',lambda *a,**k:search_result())
    monkeypatch.setattr('web.research_files._Reservation.save',lambda *a,**k:(_ for _ in ()).throw(OSError('secret path')))
    response=client.post('/api/research/search',json={'source_id':'S1','query':'context'})
    assert response.status_code==503
    assert response.json()['detail']['saved_in_database'] is True
    assert 'reload' in response.json()['detail']['message']
    assert client.get('/api/research/artifacts').json()=={'items':[]}


def test_browser_search_real_service_cache_dedup_and_user_state(monkeypatch,workspace):
    from config import RadarConfig
    from sources.venues import VenueSearchResult
    client,paper_id,db,root=workspace
    monkeypatch.setattr('web.research_api.RadarConfig.load',lambda:RadarConfig(source_cache_ttl=3600))
    venue=Venue('S1','Test Journal','journal',None,(),None,'https://api.openalex.org/sources/S1','2026-10-14T00:00:00+00:00')
    paper=Paper(source='openalex',title='Synthetic context',doi='10.1234/context',external_id='https://openalex.org/W1',venue='Test Journal')
    calls=[]
    def response(*args,**kwargs):
        calls.append(args)
        return VenueSearchResult(venue,[paper],1,False,1,20,{'provider':'openalex','source_id':'S1','retrieved_at':'2026-10-14T00:00:00+00:00','record_url':'https://api.openalex.org/works'})
    monkeypatch.setattr('web.research_api.venues.search_venue',response)
    payload={'source_id':'S1','query':'context'}
    first=client.post('/api/research/search',json=payload)
    second=client.post('/api/research/search',json=payload)
    assert first.status_code==second.status_code==200
    assert first.json()['paper_ids']==second.json()['paper_ids']==[paper_id]
    assert second.json()['cache_hit'] and len(calls)==1
    assert first.json()['artifact']['identifier']!=second.json()['artifact']['identifier']
    store=PaperStore(db)
    assert store.total_count()==1 and store.get(paper_id)['notes']=='Personal test note'
    store.close()
    assert len(list(root.iterdir()))==2
