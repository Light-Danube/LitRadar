"""Only synthetic uploads; no provider, model, server path or personal data."""
import base64

import pytest
pytest.importorskip('fastapi', reason='optional browser workspace dependency')
pytest.importorskip('httpx', reason='optional TestClient dependency')
from fastapi import FastAPI
from fastapi.testclient import TestClient
import web.local_import_api as api


def upload(filename='Наука.ris', content=b'TY  - JOUR\nTI  - Synthetic\nER  -\n', kind='ris'):
    return {'filename': filename, 'format': kind, 'content_base64': base64.b64encode(content).decode('ascii')}


@pytest.fixture
def client(tmp_path):
    app = FastAPI()
    api.register_local_import_routes(app, tmp_path/'synthetic.sqlite')
    return TestClient(app)


def test_preview_decodes_only_selected_uploaded_bytes(client, monkeypatch):
    calls = []
    def execute(db, files, payload, commit):
        calls.append((files, commit))
        return {'token': 'a'*64, 'items': [], 'counts': {}}
    monkeypatch.setattr(api, '_execute', execute)
    result = client.post('/api/local-import/preview', json={'files': [upload('C:\\private\\Наука.ris')]})
    assert result.status_code == 200
    assert calls[0][0] == [{'filename': 'Наука.ris', 'format': 'ris', 'content': b'TY  - JOUR\nTI  - Synthetic\nER  -\n'}]
    assert calls[0][1] is False


@pytest.mark.parametrize('payload', [None, [], {}, {'files': []}, {'files': [upload()], 'path': '/private'},
    {'files': [dict(upload(), url='https://private.invalid/secret')]}, {'files': [upload(content=b'')]},
    {'files': [upload(filename='../')]}, {'files': [upload(filename='bad\x00.ris')]},
    {'files': [dict(upload(), content_base64='%%%')]}, {'files': [upload(kind='zip')]},
    {'files': [upload()]*11}, {'files': [dict(upload(), format=['ris'])]}])
def test_invalid_batch_never_opens_storage(client, monkeypatch, payload):
    monkeypatch.setattr(api, '_execute', lambda *a, **kw: pytest.fail('invalid input reached storage'))
    response = client.post('/api/local-import/preview', json=payload, headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert response.json()['detail']['status'] == 'import_invalid'


def test_stream_limit_before_json_or_base64(client, monkeypatch):
    monkeypatch.setattr(api, 'MAX_BODY', 30)
    monkeypatch.setattr(api, '_execute', lambda *a, **kw: pytest.fail('oversize reached storage'))
    assert client.post('/api/local-import/preview', json={'files': [upload()]}).status_code == 413


def test_decoded_aggregate_and_per_file_caps(client, monkeypatch):
    monkeypatch.setattr(api, '_execute', lambda *a, **kw: pytest.fail('oversize reached storage'))
    monkeypatch.setattr(api, 'MAX_FILE_BYTES', 3)
    assert client.post('/api/local-import/preview', json={'files': [upload(content=b'1234')]}).status_code == 422
    monkeypatch.setattr(api, 'MAX_FILE_BYTES', 5)
    monkeypatch.setattr(api, 'MAX_TOTAL_BYTES', 5)
    assert client.post('/api/local-import/preview', json={'files': [upload(content=b'123'), upload(content=b'456')]}).status_code == 422


@pytest.mark.parametrize('extra', [{}, {'token': 'wrong', 'selected_indices': [0]},
    {'token': 'a'*64, 'selected_indices': []}, {'token': 'a'*64, 'selected_indices': [True]},
    {'token': 'a'*64, 'selected_indices': [-1]}, {'token': 'a'*64, 'selected_indices': [0, 0]},
    {'token': 'a'*64, 'selected_indices': [500]}, {'token': 'a'*64, 'selected_indices': [0], 'overwrite': True}])
def test_commit_requires_valid_preview_and_explicit_selection(client, monkeypatch, extra):
    monkeypatch.setattr(api, '_execute', lambda *a, **kw: pytest.fail('invalid commit reached storage'))
    assert client.post('/api/local-import/commit', json={'files': [upload()], **extra}).status_code == 422


def test_commit_forwards_only_explicit_indices(client, monkeypatch):
    calls = []
    monkeypatch.setattr(api, '_execute', lambda db, files, payload, commit:
                        (calls.append((payload['token'], payload['selected_indices'], commit)) or {'added': 1, 'duplicates': 0, 'batch_id': 'test'}))
    result = client.post('/api/local-import/commit', json={'files': [upload()], 'token': 'b'*64, 'selected_indices': [2, 0]})
    assert result.status_code == 200
    assert calls == [('b'*64, [2, 0], True)]


def test_backend_errors_are_safe(client, monkeypatch, tmp_path):
    core = pytest.importorskip('storage.local_import')
    def fail(*args, **kwargs):
        raise core.StaleImportError('PRIVATE_PROVIDER_URL_AND_CONTENT')
    monkeypatch.setattr(core, 'commit_import', fail)
    response = client.post('/api/local-import/commit', json={'files': [upload()], 'token': 'a'*64, 'selected_indices': [0]})
    assert response.status_code == 409
    assert response.json()['detail']['status'] == 'import_stale'
    assert 'PRIVATE' not in response.text
    def invalid(*args, **kwargs):
        raise ValueError('PRIVATE_UPLOAD_CONTENT')
    monkeypatch.setattr(core, 'preview_import', invalid)
    response = client.post('/api/local-import/preview', json={'files': [upload()]})
    assert response.status_code == 422
    assert 'PRIVATE' not in response.text


def test_json_content_type_required_before_storage(client, monkeypatch):
    monkeypatch.setattr(api, '_execute', lambda *a, **kw: pytest.fail('non-JSON request reached storage'))
    response = client.post('/api/local-import/preview', content='{"files":[]}', headers={'Content-Type': 'text/plain'})
    assert response.status_code == 415
    assert response.json()['detail']['status'] == 'import_invalid'


def test_real_preview_commit_repeat_and_stale_without_preview_database_writes(client, tmp_path):
    from storage.sqlite import PaperStore
    target = tmp_path/'synthetic.sqlite'
    payload = {'files': [upload(content=b'TY  - JOUR\nTI  - Synthetic local article\nDO  - 10.1234/local.test\nER  -\n')]}
    preview = client.post('/api/local-import/preview', json=payload)
    assert preview.status_code == 200, preview.text
    data = preview.json()
    assert data['items'][0]['status'] == 'new', data
    assert not target.exists(), 'preview must not create/migrate the user database'
    commit_payload = {**payload, 'token': data['token'], 'selected_indices': [0]}
    saved = client.post('/api/local-import/commit', json=commit_payload)
    assert saved.status_code == 200, saved.text
    assert saved.json()['added'] == 1
    store = PaperStore(target)
    try:
        assert store.conn.execute('SELECT COUNT(*) FROM papers').fetchone()[0] == 1
        paper_id = saved.json()['paper_ids'][0]
        store.conn.execute('UPDATE papers SET notes=? WHERE id=?', ('Preserve reviewed note', paper_id))
        store.conn.commit()
    finally:
        store.close()
    stale = client.post('/api/local-import/commit', json=commit_payload)
    assert stale.status_code == 409
    before = target.read_bytes()
    repeated_preview = client.post('/api/local-import/preview', json=payload)
    assert target.read_bytes() == before
    assert repeated_preview.status_code == 200
    repeated = repeated_preview.json()
    assert repeated['items'][0]['status'] == 'duplicate'
    repeat_saved = client.post('/api/local-import/commit', json={**payload, 'token': repeated['token'], 'selected_indices': [0]})
    assert repeat_saved.status_code == 200, repeat_saved.text
    assert repeat_saved.json()['added'] == 0
    assert repeat_saved.json()['duplicates'] == 1
    store = PaperStore(target)
    try:
        assert store.conn.execute('SELECT COUNT(*) FROM papers').fetchone()[0] == 1
        assert store.conn.execute('SELECT notes FROM papers WHERE id=?', (paper_id,)).fetchone()[0] == 'Preserve reviewed note'
    finally:
        store.close()
