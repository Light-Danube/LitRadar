import numpy as np
import pytest
pytest.importorskip('fastapi')
pytest.importorskip('httpx')
from fastapi.testclient import TestClient
from sources.base import Paper
from storage.sqlite import PaperStore
from workspace_web import create_app

class FakeEmbedder:
    model_name='synthetic-local'
    def __init__(self):self.calls=0
    def encode(self,texts):
        self.calls+=1
        return np.asarray([[1.,0.] if 'Related' in text else [0.,1.] for text in texts])

@pytest.fixture
def workspace(tmp_path):
    path=tmp_path/'semantic-synthetic.sqlite3';store=PaperStore(path)
    ids=[store.upsert_paper(Paper(source='fixture',title=title,abstract='Synthetic',published_at=year),relevance_score=.5,matched_groups={}) for title,year in [('Related seed','2020'),('Related neighbor','2021'),('Different topic','2022')]]
    store.close();return path,ids

def test_semantic_requests_are_explicit_and_off_by_default(workspace):
    path,ids=workspace;embedder=FakeEmbedder();client=TestClient(create_app(path,semantic_enabled=False,semantic_embedder=embedder))
    assert client.get('/api/graph').status_code==200
    assert client.get('/api/clusters').json()['method']=='heuristic'
    assert client.get('/api/graph?include_semantic=true').status_code==409
    assert client.get('/api/clusters?mode=semantic').status_code==409
    assert embedder.calls==0

def test_semantic_seed_navigation_is_related_ephemeral_and_never_persisted(workspace):
    path,(seed,neighbor,other)=workspace;embedder=FakeEmbedder();client=TestClient(create_app(path,semantic_enabled=True,semantic_embedder=embedder))
    data=client.get(f'/api/graph?seed_id={seed}&include_semantic=true').json()
    assert {p['id'] for p in data['nodes']}=={seed,neighbor}
    edge=data['edges'][0];assert edge['type']=='related' and edge['providers']==['embedding:synthetic-local']
    assert edge['provenance'][0]['ephemeral'] is True and edge['similarity']==1
    assert client.get(f'/api/graph?seed_id={seed}').json()['edges']==[]
    assert client.get(f'/api/graph?seed_id={seed}&include_semantic=true&relation=cites').json()['edges']==[]
    assert client.get(f'/api/graph?seed_id={seed}&include_semantic=true&provider=openalex').json()['edges']==[]
    excluded=client.get(f'/api/graph?seed_id={seed}&include_semantic=true&year_to=2020').json()
    assert excluded['edges']==[] and {p['id'] for p in excluded['nodes']}=={seed}
    store=PaperStore(path);assert store.conn.execute('SELECT COUNT(*) FROM paper_relations').fetchone()[0]==0;store.close()

def test_semantic_cache_keeps_current_workflow_metadata(workspace):
    path,ids=workspace;embedder=FakeEmbedder();client=TestClient(create_app(path,semantic_enabled=True,semantic_embedder=embedder))
    first=client.get('/api/clusters?mode=semantic').json();assert first['method']=='embedding'
    assert sorted(c['size'] for c in first['clusters'])==[1,2]
    client.patch(f'/api/papers/{ids[0]}',json={'status':'read','notes':'New local note'})
    second=client.get('/api/clusters?mode=semantic').json()
    found=next(p for c in second['clusters'] for p in c['papers'] if p['id']==ids[0])
    assert found['notes']=='New local note' and found['status']=='read' and embedder.calls==1

def test_enabled_without_model_never_falls_back_or_downloads(workspace,monkeypatch):
    path,_=workspace
    monkeypatch.delenv('LITBEACON_EMBEDDING_MODEL_PATH',raising=False);monkeypatch.delenv('LITRADAR_EMBEDDING_MODEL_PATH',raising=False)
    client=TestClient(create_app(path,semantic_enabled=True))
    assert client.get('/api/clusters').status_code==200
    assert client.get('/api/clusters?mode=semantic').status_code==503
    assert client.get('/api/graph?include_semantic=true').status_code==503

def test_computed_related_provenance_merges_without_relabelling_real_citations(workspace):
    path,(seed,neighbor,other)=workspace
    store=PaperStore(path);store.record_relation(seed,neighbor,'related','openalex');store.record_relation(neighbor,seed,'cites','semantic_scholar');store.close()
    client=TestClient(create_app(path,semantic_enabled=True,semantic_embedder=FakeEmbedder()))
    data=client.get(f'/api/graph?seed_id={seed}&include_semantic=true').json()
    related=[e for e in data['edges'] if e['type']=='related'];cites=[e for e in data['edges'] if e['type']=='cites']
    assert len(related)==1 and set(related[0]['providers'])=={'openalex','embedding:synthetic-local'}
    assert len(cites)==1 and (cites[0]['source'],cites[0]['target'])==(str(neighbor),str(seed))
    assert not any(p.get('ephemeral') for p in cites[0]['provenance'])
    store=PaperStore(path);assert store.conn.execute('SELECT COUNT(*) FROM paper_relations').fetchone()[0]==2;store.close()
