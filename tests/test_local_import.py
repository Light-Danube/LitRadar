"""Synthetic, offline local-bibliography import contracts."""
import io
import json
from pathlib import Path
import socket
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sources.base import Paper
from storage.sqlite import PaperStore
from storage import local_import as importer


@pytest.fixture
def store(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError('local import must remain offline')
    monkeypatch.setattr(socket, 'create_connection', no_network)
    monkeypatch.setattr(socket.socket, 'connect', no_network)
    value = PaperStore(tmp_path / 'library.sqlite3')
    yield value
    value.close()


def ris(title='Українська наукова праця', doi='10.1234/example', extra='', filename='selected.ris'):
    return {'filename': filename, 'format': 'ris', 'content': (
        f'TY  - JOUR\nTI  - {title}\nDO  - {doi}\nAU  - Дослідник, Олена\nPY  - 2025\n{extra}ER  - \n').encode()}


def count(store, table):
    return store.conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]


def test_unicode_preview_is_read_only_and_commit_provenance(store):
    files = [ris(extra='LA  - uk\nUR  - https://example.invalid/article\nL1  - /private/paper.pdf\n',
                 filename='/private/research/selected.ris')]
    before = store.conn.total_changes
    plan = importer.preview_import(store, files)
    assert plan == importer.preview_import(store, files)
    assert store.conn.total_changes == before
    assert plan['items'][0]['title'] == 'Українська наукова праця'
    assert plan['items'][0]['filename'] == 'selected.ris'
    assert plan['counts']['new'] == 1
    result = importer.commit_import(store, files, plan['token'])
    row = store.get(result['paper_ids'][0])
    assert result['added'] == result['observations_added'] == 1
    raw = json.loads(row['raw_json'])
    assert raw['filename'] == 'selected.ris' and raw['publication_language'] == 'uk'
    assert 'L1' not in raw['fields'] and '/private/' not in json.dumps(raw)
    assert row['source'] == 'local_import'
    assert importer.list_batches(store)[0]['batch_id'] == result['batch_id']


def test_duplicate_preserves_all_canonical_fields_and_annotations(store):
    paper_id = store.upsert_paper(Paper(source='openalex', title='Українська наукова праця',
        doi='https://doi.org/10.1234/example', authors=['Дослідник, Олена'], abstract='Existing abstract'),
        relevance_score=8, matched_groups={'group': ['term']})
    store.set_notes(paper_id, 'User notes')
    store.set_status(paper_id, 'to-read')
    store.add_tags(paper_id, ['manual'])
    store.add_annotation(paper_id, 'User annotation')
    before = dict(store.get(paper_id))
    annotations = [tuple(row) for row in store.conn.execute('SELECT * FROM paper_annotations')]
    files = [ris(extra='AB  - Imported abstract\n')]
    plan = importer.preview_import(store, files)
    assert plan['counts']['duplicate'] == 1
    result = importer.commit_import(store, files, plan['token'])
    assert result['added'] == 0 and result['duplicates'] == 1
    assert dict(store.get(paper_id)) == before
    assert [tuple(row) for row in store.conn.execute('SELECT * FROM paper_annotations')] == annotations
    again = importer.commit_import(store, files, importer.preview_import(store, files)['token'])
    assert again['observations_added'] == 0 and count(store, 'papers') == 1


def test_stale_matching_record_and_changed_bytes_are_atomic(store):
    files = [ris()]
    token = importer.preview_import(store, files)['token']
    with pytest.raises(importer.StaleImportError):
        importer.commit_import(store, [ris(title='Changed')], token)
    assert count(store, 'papers') == count(store, 'local_import_batches') == 0
    result = importer.commit_import(store, files, token)
    current = importer.preview_import(store, files)['token']
    store.set_notes(result['paper_ids'][0], 'Concurrent note')
    with pytest.raises(importer.StaleImportError):
        importer.commit_import(store, files, current)
    assert count(store, 'local_import_batches') == 1


def test_batch_duplicate_conflict_and_selection(store):
    files = [ris(), ris(filename='second.ris'), ris(title='Contradictory title', filename='third.ris')]
    plan = importer.preview_import(store, files)
    assert [item['status'] for item in plan['items']] == ['new', 'duplicate', 'conflict']
    with pytest.raises(importer.ImportValidationError):
        importer.commit_import(store, files, plan['token'], [2])
    assert count(store, 'papers') == 0
    result = importer.commit_import(store, files, plan['token'], [0, 1])
    assert result['added'] == result['duplicates'] == 1
    assert count(store, 'local_import_observations') == 1  # same bytes and record are repeat-safe


def test_same_title_different_doi_and_ambiguous_title_are_not_merged(store):
    for doi in ['10.1234/first', '10.1234/second']:
        store.upsert_paper(Paper(source='test', title='Ambiguous title', doi=doi),
                           relevance_score=1, matched_groups={})
    # Canonical storage may have merged equal titles; construct a second existing
    # title candidate using its supported update API, then check ambiguity.
    other = store.upsert_paper(Paper(source='test', title='Different initial title', doi='10.1234/third'),
                              relevance_score=1, matched_groups={})
    existing = store.conn.execute('SELECT title_normalized,title_hash FROM papers LIMIT 1').fetchone()
    store.conn.execute('UPDATE papers SET title=?,title_normalized=?,title_hash=? WHERE id=?',
                       ('Ambiguous title', existing[0], existing[1], other))
    store.conn.commit()
    assert importer.preview_import(store, [ris(title='Ambiguous title', doi='')])['counts']['conflict'] == 1
    assert importer.preview_import(store, [ris(title='Ambiguous title', doi='10.1234/other')])['counts']['conflict'] == 1


def test_malformed_file_can_only_be_explicitly_excluded(store):
    files = [ris(), {'filename': 'broken.ris', 'format': 'ris', 'content': b'not RIS'}]
    plan = importer.preview_import(store, files)
    assert plan['counts']['failed'] == 1
    assert plan['items'][1]['message_code'] == 'invalid_file'
    assert importer.commit_import(store, files, plan['token'], [0])['added'] == 1


@pytest.mark.parametrize('files', [[], [{'filename':'x','format': [],'content': b'x'}],
    [{'filename':'x','format':'ris','content':b''}],
    [{'filename':'x','format':'ris','content':b'x','path':'/private'}]])
def test_structural_validation(store, files):
    with pytest.raises(importer.ImportValidationError):
        importer.preview_import(store, files)
    assert count(store, 'local_import_batches') == 0


def test_commit_failure_rolls_back_papers_and_journal(store, monkeypatch):
    files = [ris(), ris(title='Other paper', doi='10.1234/other', filename='other.ris')]
    plan = importer.preview_import(store, files)
    original = store._upsert_paper_no_commit
    calls = 0
    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError('Synthetic failure')
        return original(*args, **kwargs)
    monkeypatch.setattr(store, '_upsert_paper_no_commit', fail_second)
    with pytest.raises(RuntimeError):
        importer.commit_import(store, files, plan['token'])
    assert count(store, 'papers') == count(store, 'local_import_batches') == count(store, 'local_import_observations') == 0


def test_optional_parser_absent_is_explicit_and_never_writes(store, monkeypatch):
    monkeypatch.setattr(importer.importlib.util, 'find_spec', lambda name: None)
    plan = importer.preview_import(store, [{'filename':'x.pdf','format':'pdf','content': b'%PDF-invalid'}])
    assert plan['counts']['failed'] == 1 and 'missing optional parser' in plan['items'][0]['message']
    with pytest.raises(importer.ImportValidationError):
        importer.commit_import(store, [{'filename':'x.pdf','format':'pdf','content':b'%PDF-invalid'}], plan['token'])


def test_bibtex_unicode_and_attachment_paths(store):
    pytest.importorskip('bibtexparser')
    files = [{'filename':'references.bib','format':'bibtex','content': (
        '@article{example,title={Українська публікація},author={Олена Дослідник and Іван Автор},'
        'doi={10.1234/bib},year={2024},file={/private/secret.pdf},'
        'pdf={/private/pdf.pdf},bdsk-file-1={/private/bibdesk.pdf},local-url={file:///private/local.pdf}}').encode()}]
    plan = importer.preview_import(store, files)
    assert plan['counts']['new'] == 1
    assert plan['items'][0]['metadata']['authors'] == ['Олена Дослідник', 'Іван Автор']
    assert '/private/' not in json.dumps(plan)


def test_title_only_duplicate_keeps_canonical_doi_missing(store):
    paper_id = store.upsert_paper(Paper(source='existing', title='Українська наукова праця'),
                                 relevance_score=3, matched_groups={})
    before = dict(store.get(paper_id))
    files = [ris()]
    plan = importer.preview_import(store, files)
    assert plan['items'][0]['paper_id'] == paper_id
    assert plan['counts']['duplicate'] == 1
    importer.commit_import(store, files, plan['token'])
    assert dict(store.get(paper_id)) == before
    observation = store.conn.execute('SELECT metadata_json FROM local_import_observations').fetchone()[0]
    assert json.loads(observation)['doi'] == '10.1234/example'


def test_repeat_after_canonical_correction_does_not_create_another_paper(store):
    files = [ris(doi='')]
    result = importer.commit_import(store, files, importer.preview_import(store, files)['token'])
    corrected = Paper(source='local_import', title='Corrected bibliographic title')
    store.conn.execute('UPDATE papers SET title=?,title_normalized=?,title_hash=? WHERE id=?',
                       (corrected.title, corrected.title_normalized, corrected.title_hash, result['paper_ids'][0]))
    store.conn.commit()
    plan = importer.preview_import(store, files)
    assert plan['counts']['conflict'] == 1
    assert plan['items'][0]['paper_id'] == result['paper_ids'][0]
    with pytest.raises(importer.ImportValidationError):
        importer.commit_import(store, files, plan['token'])
    assert count(store, 'papers') == count(store, 'local_import_observations') == 1


def test_pdf_metadata_only_missing_title_and_encryption(store):
    pypdf = pytest.importorskip('pypdf')
    def pdf(title=None, encrypted=False):
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=72,height=72)
        if title:
            writer.add_metadata({'/Title':title,'/Author':'Олена Дослідник'})
        if encrypted:
            writer.encrypt('password')
        output = io.BytesIO()
        writer.write(output)
        return {'filename':'paper.pdf','format':'pdf','content':output.getvalue()}
    plan = importer.preview_import(store, [pdf('Український PDF'), pdf(), pdf('Encrypted PDF', True)])
    assert [item['status'] for item in plan['items']] == ['new','skipped','failed']
    assert plan['items'][0]['confidence'] == 'low'
    assert plan['items'][0]['metadata']['abstract'] == ''
    assert plan['items'][0]['metadata']['raw']['pdf_metadata_only'] is True


def test_record_limit_applies_across_valid_and_failed_files(store):
    files = [dict(ris(), content=ris()['content'] * importer.MAX_RECORDS),
             {'filename':'broken.ris','format':'ris','content':b'broken'}]
    with pytest.raises(importer.ImportValidationError):
        importer.preview_import(store, files)
    assert count(store, 'papers') == 0


def test_file_and_batch_byte_limits_reject_before_parse(store):
    with pytest.raises(importer.ImportValidationError):
        importer.preview_import(store, [dict(ris(), content=b'x' * (importer.MAX_FILE_BYTES + 1))])
    with pytest.raises(importer.ImportValidationError):
        importer.preview_import(store, [dict(ris(), content=b'x' * importer.MAX_FILE_BYTES)] * 3)


def test_parser_result_shape_is_safe_failure(store, monkeypatch):
    monkeypatch.setattr(importer, '_parse', lambda file, deadline: [None])
    plan = importer.preview_import(store, [ris()])
    assert plan['counts']['failed'] == 1
    assert plan['items'][0]['message_code'] == 'invalid_metadata'
