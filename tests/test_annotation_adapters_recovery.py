import base64
import io
import json
import sqlite3
from types import SimpleNamespace

import pytest

pytest.importorskip('fastapi')
pytest.importorskip('httpx')
from fastapi.testclient import TestClient
from sources.base import Paper
from storage.sqlite import PaperStore
from workspace_web import create_app
from web import annotation_actions as actions


@pytest.fixture
def workspace(tmp_path):
    path = tmp_path / 'synthetic.sqlite3'
    with_store = PaperStore(path)
    one = with_store.upsert_paper(Paper(source='fixture',title='Synthetic evidence',abstract='No personal data.'),relevance_score=.5,matched_groups={})
    two = with_store.upsert_paper(Paper(source='fixture',title='Other paper'),relevance_score=.5,matched_groups={})
    with_store.set_notes(one, 'Original')
    with_store.close()
    return TestClient(create_app(path)), path, one, two


def upload(client, paper, name, content, format):
    return client.post(f'/api/papers/{paper}/annotations/import-files', json={'files':[file_entry(name,content,format)]})


def file_entry(name, content, format):
    data = content.encode('utf-8') if isinstance(content,str) else content
    return {'filename':name,'format':format,'content_base64':base64.b64encode(data).decode('ascii')}


def test_research_note_restore_appends_history_and_rejects_stale_and_cross_paper(workspace):
    client,path,paper,other = workspace
    old = client.get(f'/api/papers/{paper}/notes/history').json()['items'][0]
    client.patch(f'/api/papers/{paper}',json={'notes':'New'})
    latest = client.get(f'/api/papers/{paper}/notes/history').json()['items'][0]
    url = f'/api/papers/{paper}/notes/history/{old["id"]}/restore'
    assert client.post(url,json={'expected_note_id':old['id']}).status_code == 409
    result = client.post(url,json={'expected_note_id':latest['id']})
    assert result.status_code == 200 and result.json()['notes'] == 'Original'
    history = client.get(f'/api/papers/{paper}/notes/history').json()['items']
    assert len(history)==3 and history[0]['origin_method']=='history_restore'
    assert history[0]['kind']=='user' and history[-1]['content']=='Original'
    assert client.post(f'/api/papers/{other}/notes/history/{old["id"]}/restore',json={'expected_note_id':None}).status_code==404
    # Clearing is a historical revision too and can be restored.
    client.patch(f'/api/papers/{paper}',json={'notes':''})
    empty = client.get(f'/api/papers/{paper}/notes/history').json()['items'][0]
    assert client.post(url,json={'expected_note_id':empty['id']}).status_code==200
    newest=client.get(f'/api/papers/{paper}/notes/history').json()['items'][0]
    assert client.post(f'/api/papers/{paper}/notes/history/{empty["id"]}/restore',json={'expected_note_id':newest['id']}).json()['notes']==''


def test_delete_restore_and_version_restore_preserve_provenance_and_conflicts(workspace):
    client,path,paper,other = workspace
    prefix=f'/api/papers/{paper}/annotations'
    item=client.post(prefix,json={'content':'Original supplement','kind':'imported','source_ref':'fixture'}).json()
    url=f'{prefix}/{item["id"]}'
    edited=client.patch(url,json={'expected_revision':1,'content':'Edited','review_status':'accepted'}).json()
    deleted=client.request('DELETE',url,json={'expected_revision':edited['revision']}).json()
    assert deleted['deleted_at'] and deleted['revision']==3
    assert not client.get(prefix).json()['items']
    assert client.get(prefix+'?deleted=true').json()['items'][0]['id']==item['id']
    assert client.patch(url,json={'expected_revision':3,'content':'Forbidden edit'}).status_code==409
    assert client.post(url+'/restore',json={'expected_revision':2}).status_code==409
    restored=client.post(url+'/restore',json={'expected_revision':3}).json()
    assert restored['deleted_at'] is None and restored['content']=='Edited' and restored['review_status']=='accepted'
    historic=client.post(url+'/restore',json={'expected_revision':4,'restore_revision':1}).json()
    assert historic['content']=='Original supplement' and historic['kind']=='imported' and historic['source_ref']=='fixture'
    assert historic['origin_method']=='declared' and historic['revision']==5
    page=client.get(url+'/history?limit=2').json()
    assert [r['revision'] for r in page['items']]==[5,4] and page['next_before_revision']==4
    assert [r['revision'] for r in client.get(url+'/history?before_revision=4').json()['items']]==[3,2,1]
    assert client.post(f'/api/papers/{other}/annotations/{item["id"]}/restore',json={'expected_revision':5}).status_code==404
    assert client.post(url+'/restore',json={'expected_revision':5,'restore_revision':99}).status_code==404
    assert client.get(f'/api/papers/{paper}').json()['notes']=='Original'


def test_json_ris_batch_is_atomic_repeat_safe_and_does_not_revive_deleted(workspace):
    client,path,paper,_=workspace
    ris='TY  - JOUR\nTI  - Synthetic\nAB  - Evidence\nN1  - Українська нотатка\nER  -\n'
    entries=[file_entry('notes.json',json.dumps([{'content':'First','source_ref':None}]),'json'),file_entry('synthetic.ris',ris,'ris')]
    url=f'/api/papers/{paper}/annotations/import-files'
    result=client.post(url,json={'files':entries})
    assert result.status_code==200 and result.json()['added']==2
    assert {i['origin_method'] for i in result.json()['items']}=={'json_import','ris_import'}
    assert client.post(url,json={'files':entries}).json()['added']==0
    item=result.json()['items'][0]
    client.request('DELETE',f'/api/papers/{paper}/annotations/{item["id"]}',json={'expected_revision':1})
    assert client.post(url,json={'files':entries}).json()['added']==0
    assert len(client.get(f'/api/papers/{paper}/annotations?deleted=true').json()['items'])==1
    before=len(client.get(f'/api/papers/{paper}/annotations').json()['items'])
    malformed=[file_entry('good.json','[{"content":"Never committed"}]','json'),file_entry('bad.ris','TY  - JOUR\nTI  - Missing ER','ris')]
    assert client.post(url,json={'files':malformed}).status_code==422
    assert len(client.get(f'/api/papers/{paper}/annotations').json()['items'])==before


@pytest.mark.parametrize('payload',[
    {'files':[{'filename':'bad.json','format':'json','content_base64':'not base64!'}]},
    {'files':[file_entry('bad.json','{"content":"not an array"}','json')]},
    {'files':[file_entry('bad.json',json.dumps([{'content':'Fake','kind':'generated'}]),'json')]},
    {'files':[file_entry('too-many.json',json.dumps([{'content':'x'}]*101),'json')]},
])
def test_invalid_uploads_leave_no_records(workspace,payload):
    client,_,paper,_=workspace
    assert client.post(f'/api/papers/{paper}/annotations/import-files',json=payload).status_code==422
    assert client.get(f'/api/papers/{paper}/annotations').json()['items']==[]


def test_upload_stream_is_bounded_before_parsing(workspace):
    client,_,paper,_=workspace
    response=client.post(f'/api/papers/{paper}/annotations/import-files',content=b' '*7000001)
    assert response.status_code==413


@pytest.mark.skipif(not actions.adapter_capabilities()['bibtex'],reason='Optional BibTeX adapter is not installed')
def test_bibtex_adapter_unicode_nested_fields_and_invalid_batch(workspace):
    client,_,paper,_=workspace
    response=upload(client,paper,'synthetic.bib','@article{fixture, title={Synthetic {nested} title}, abstract={Докази}, note={Read cautiously}}','bibtex')
    assert response.status_code==200, response.text
    item=response.json()['items'][0]
    assert item['origin_method']=='bibtex_import' and 'Докази' in item['content']
    bad=upload(client,paper,'bad.bib','@article{broken, title={Missing braces','bibtex')
    assert bad.status_code==422


@pytest.mark.skipif(not actions.adapter_capabilities()['pdf'],reason='Optional PDF adapter is not installed')
def test_pdf_adapter_reads_only_synthetic_comments_and_rejects_invalid_pdf(workspace):
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, DictionaryObject, NameObject, TextStringObject, FloatObject
    client,_,paper,_=workspace
    writer=PdfWriter();page=writer.add_blank_page(width=200,height=200)
    annotation=DictionaryObject({NameObject('/Type'):NameObject('/Annot'),NameObject('/Subtype'):NameObject('/Text'),
        NameObject('/Rect'):ArrayObject([FloatObject(x) for x in [10,10,40,40]]),NameObject('/Contents'):TextStringObject('Synthetic PDF comment')})
    page[NameObject('/Annots')]=ArrayObject([writer._add_object(annotation)])
    output=io.BytesIO();writer.write(output)
    response=upload(client,paper,'synthetic.pdf',output.getvalue(),'pdf')
    assert response.status_code==200, response.text
    assert response.json()['items'][0]['content']=='Synthetic PDF comment'
    assert response.json()['items'][0]['origin_method']=='pdf_import'
    assert upload(client,paper,'bad.pdf',b'not a PDF','pdf').status_code==422


@pytest.mark.parametrize('provider_id',['openai','anthropic','ollama'])
def test_fresh_generation_requires_consent_uses_only_metadata_and_records_provider(workspace,monkeypatch,provider_id):
    client,_,paper,_=workspace;calls=[]
    monkeypatch.setattr(actions,'available_providers',lambda:[{'id':provider_id,'available':True,'model':'fixture'}])
    import llm.providers
    def complete(prompt):
        calls.append(prompt)
        return json.dumps({'summary':'Synthetic generated summary','questions':['Verify evidence']})
    monkeypatch.setattr(llm.providers,'make_provider',lambda *args:SimpleNamespace(name=provider_id,model='fixture',complete=complete,max_tokens=None,max_retries=2))
    url=f'/api/papers/{paper}/annotations/generate'
    assert client.post(url,json={'provider':provider_id}).status_code==422 and not calls
    response=client.post(url,json={'provider':provider_id,'consent':True,'language':'uk'})
    assert response.status_code==200, response.text
    item=response.json()['items'][0]
    assert item['origin_method']=='fresh_llm' and item['kind']=='generated' and item['review_status']=='unreviewed'
    assert f'{provider_id} / fixture' in item['source_ref'] and 'sha256=' in item['source_ref']
    assert 'Original' not in calls[0] and 'Ukrainian' in calls[0]
    assert client.get(f'/api/papers/{paper}').json()['notes']=='Original'
    assert client.post(url,json={'provider':provider_id,'consent':True,'language':'uk'}).json()['added']==0


@pytest.mark.parametrize('error_type',[RuntimeError,ValueError])
def test_provider_failure_is_sanitized_and_no_annotation_is_committed(workspace,monkeypatch,error_type):
    client,_,paper,_=workspace
    monkeypatch.setattr(actions,'available_providers',lambda:[{'id':'ollama','available':True}])
    import llm.providers
    def fail(prompt): raise error_type('Synthetic secret must not be echoed')
    monkeypatch.setattr(llm.providers,'make_provider',lambda *args:SimpleNamespace(name='ollama',model='fixture',complete=fail))
    response=client.post(f'/api/papers/{paper}/annotations/generate',json={'provider':'ollama','consent':True})
    assert response.status_code==502 and 'Synthetic secret' not in response.text
    assert client.get(f'/api/papers/{paper}/annotations').json()['items']==[]


def test_migration_reopen_keeps_old_rows_and_revisions(workspace):
    client,path,paper,_=workspace
    item=client.post(f'/api/papers/{paper}/annotations',json={'content':'Persisted'}).json()
    # Reconstruct the pre-recovery schema on a disposable DB.
    conn=sqlite3.connect(path)
    conn.execute('ALTER TABLE paper_annotations DROP COLUMN deleted_at')
    conn.execute('ALTER TABLE annotation_revisions DROP COLUMN deleted_at')
    conn.commit();conn.close()
    store=PaperStore(path)
    assert store.list_annotations(paper)[0]['content']=='Persisted'
    assert len(store.annotation_history(paper,item['id']))==1
    store.close()


def test_legacy_json_import_and_new_file_import_share_repeat_safe_identity(workspace):
    client,_,paper,_=workspace
    first=client.post(f'/api/papers/{paper}/annotations/import',json={'filename':'same.json','items':[{'content':'Existing import'}]})
    assert first.status_code==200 and first.json()['added']==1
    repeated=upload(client,paper,'same.json','[{"content":"Existing import"}]','json')
    assert repeated.status_code==200 and repeated.json()['added']==0
    assert len(client.get(f'/api/papers/{paper}/annotations').json()['items'])==1
