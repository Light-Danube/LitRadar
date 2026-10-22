"""Opt-in, metadata-only bibliography import. No resolver, model or file crawler."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import time
import uuid
from urllib.parse import urlsplit

from sources.base import Paper
from storage.sqlite import PaperStore, _clean_doi
from storage.local_import_parsers import parse_ris

MAX_FILES = 10
MAX_FILE_BYTES = 5_000_000
MAX_TOTAL_BYTES = 10_000_000
MAX_RECORDS = 500
MAX_PARSED_BYTES = 2_000_000
MAX_SECONDS = 30
PARSER_VERSION = 'local-bibliography-v1'
STATUSES = ('new', 'duplicate', 'conflict', 'skipped', 'failed')


class ImportValidationError(ValueError):
    pass


class StaleImportError(ImportValidationError):
    pass


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _digest(value) -> str:
    return hashlib.sha256(_json(value).encode('utf-8')).hexdigest()


def _label(filename: object) -> str:
    if not isinstance(filename, str) or not filename or len(filename) > 4096:
        raise ImportValidationError('Each file needs a bounded filename label')
    label = filename.replace('\\', '/').rsplit('/', 1)[-1]
    if not label or label in {'.', '..'} or len(label) > 255 or any(ord(c) < 32 for c in label):
        raise ImportValidationError('Invalid filename label')
    return label


def _validated_files(files) -> list[dict]:
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise ImportValidationError('Choose 1–10 individual bibliography files')
    result, total = [], 0
    for item in files:
        if not isinstance(item, dict) or set(item) != {'filename', 'format', 'content'}:
            raise ImportValidationError('Use filename, format and uploaded content only')
        if not isinstance(item['format'], str) or item['format'] not in {'ris', 'bibtex', 'pdf'}:
            raise ImportValidationError('Supported formats are RIS, BibTeX and metadata-only PDF')
        content = item['content']
        if not isinstance(content, bytes) or not 1 <= len(content) <= MAX_FILE_BYTES:
            raise ImportValidationError('Each file must contain 1 byte–5 MB')
        total += len(content)
        if total > MAX_TOTAL_BYTES:
            raise ImportValidationError('Selected files exceed 10 MB combined')
        result.append({'filename': _label(item['filename']), 'format': item['format'],
                       'content': content, 'sha256': hashlib.sha256(content).hexdigest()})
    return result


def _parse(file, deadline):
    kind, content = file['format'], file['content']
    if time.monotonic() >= deadline:
        raise ImportValidationError('Import preview exceeded its time limit')
    if kind == 'ris':
        return parse_ris(content.decode('utf-8-sig'))
    module = 'pypdf' if kind == 'pdf' else 'bibtexparser'
    if importlib.util.find_spec(module) is None:
        raise RuntimeError('Optional parser is not installed')
    worker = subprocess.run([sys.executable, '-m', 'storage.local_import_parsers', kind],
                            input=content, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            timeout=min(10, max(.01, deadline - time.monotonic())), check=False)
    if worker.returncode or len(worker.stdout) > MAX_PARSED_BYTES:
        raise ValueError('Invalid parser result')
    return json.loads(worker.stdout)


def _first(fields, *names):
    for name in names:
        values = fields.get(name)
        if values:
            return values[0].strip()
    return ''


def _safe_url(value):
    if not value:
        return None
    if len(value) > 2000:
        raise ValueError('URL too long')
    parsed = urlsplit(value)
    if parsed.scheme.casefold() not in {'https', 'http'} or not parsed.netloc or parsed.username or parsed.password:
        return None
    return value


def _paper(record, file):
    if not isinstance(record, dict) or set(record) - {'key', 'fields', 'pdf_metadata_only'}:
        raise ValueError('Invalid parsed record')
    if not isinstance(record.get('key'), str) or not re.fullmatch(r'[1-9][0-9]{0,2}', record['key']):
        raise ValueError('Invalid record key')
    fields = record.get('fields')
    if not isinstance(fields, dict) or len(fields) > 100:
        raise ValueError('Invalid metadata fields')
    for key, values in fields.items():
        if not isinstance(key, str) or not isinstance(values, list) or len(values) > 100:
            raise ValueError('Invalid field values')
        if any(not isinstance(value, str) or len(value) > 20000 for value in values):
            raise ValueError('Invalid field text')
    title = _first(fields, 'TI', 'T1', 'title')
    if not title:
        return None
    if len(title) > 2000:
        raise ValueError('Title too long')
    authors = fields.get('AU') or fields.get('A1') or fields.get('author') or []
    if file['format'] == 'bibtex':
        authors = [author.strip() for author in ' and '.join(authors).split(' and ') if author.strip()]
    elif file['format'] == 'pdf':
        authors = [author.strip() for author in ';'.join(authors).split(';') if author.strip()]
    if len(authors) > 100 or any(len(author) > 500 for author in authors):
        raise ValueError('Author bounds')
    doi = _first(fields, 'DO', 'doi')
    doi = re.sub(r'^doi:\s*', '', doi, flags=re.IGNORECASE)
    doi = _clean_doi(doi)
    if doi and (len(doi) > 2000 or not re.fullmatch(r'10\.\d{4,9}/\S+', doi)):
        raise ValueError('Invalid DOI')
    date = _first(fields, 'PY', 'Y1', 'DA', 'year', 'date')
    year = re.match(r'^(\d{4})(?:\D|$)', date)
    abstract = _first(fields, 'AB', 'N2', 'abstract')
    if len(abstract) > 20000:
        raise ValueError('Abstract bounds')
    # Keep original bibliographic fields, but never persist attachment/path
    # directives. They are neither dereferenced nor needed for provenance.
    excluded = {'file', 'files', 'path', 'attachment', 'attachments', 'localfile', 'localpath', 'filename',
                'pdf', 'local-url', 'local_url', 'l1', 'l2', 'l3', 'l4'}
    raw_fields = {key: values for key, values in fields.items()
                  if key.casefold() not in excluded and not key.casefold().startswith(('bdsk-file-', 'bdsk-url-'))}
    for key in ('url', 'UR'):
        if key in raw_fields:
            raw_fields[key] = [value for value in raw_fields[key] if _safe_url(value)]
    raw = {'fields': raw_fields, 'parser_version': PARSER_VERSION,
           'file_sha256': file['sha256'], 'filename': file['filename'],
           'format': file['format'], 'record_key': str(record.get('key', '')),
           'publication_language': _first(fields, 'LA', 'language') or None,
           'pdf_metadata_only': bool(record.get('pdf_metadata_only'))}
    key = _digest([file['sha256'], file['format'], raw['record_key']])
    return Paper(source='local_import', title=title, abstract=abstract, authors=authors,
                 published_at=year.group(1) if year else None, doi=doi,
                 url=_safe_url(_first(fields, 'UR', 'url')),
                 venue=_first(fields, 'JO', 'JF', 'T2', 'journal', 'booktitle') or None,
                 external_id=key, raw=raw)


def _metadata_conflict(left: Paper, row) -> bool:
    if left.title_normalized != row['title_normalized']:
        return True
    for incoming, existing in ((left.doi, row['doi_normalized']), (left.venue, row['venue'])):
        if incoming and existing and incoming.casefold() != existing.casefold():
            return True
    if left.published_at and row['published_at'] and left.published_at[:4] != row['published_at'][:4]:
        return True
    authors = json.loads(row['authors_json'] or '[]')
    return bool(left.authors and authors and [a.casefold() for a in left.authors] != [a.casefold() for a in authors])


def _classify(store, paper, earlier):
    observed = store.conn.execute('SELECT paper_id FROM local_import_observations WHERE observation_key=?',
                                  (paper.external_id,)).fetchone()
    if observed is not None:
        previous = store.get(observed['paper_id'])
        if previous is not None:
            if _metadata_conflict(paper, previous):
                return 'conflict', previous['id'], 'Previously imported record changed; existing paper is preserved', dict(previous), None
            return 'duplicate', previous['id'], 'Previously imported record; existing paper preserved', dict(previous), None
    titles = store.conn.execute('SELECT * FROM papers WHERE title_hash=? ORDER BY id', (paper.title_hash,)).fetchall()
    existing_id = store.find_existing_paper_id(paper)
    row = store.get(existing_id) if existing_id is not None else None
    if len(titles) > 1 and (not paper.doi or not any(r['doi_normalized'] == paper.doi for r in titles)):
        return 'conflict', None, 'Ambiguous title matches; review existing papers', None, None
    if paper.doi and any(r['doi_normalized'] and r['doi_normalized'] != paper.doi for r in titles):
        return 'conflict', None, 'Title matches a different DOI; no automatic merge', None, None
    if row is not None:
        if _metadata_conflict(paper, row):
            return 'conflict', existing_id, 'Bibliographic metadata differs; existing record is preserved', dict(row), None
        return 'duplicate', existing_id, 'Existing paper preserved; metadata observation only', dict(row), None
    for prior_index, prior in earlier:
        if paper.doi and prior.doi == paper.doi:
            conflict = (paper.title_normalized != prior.title_normalized or
                        bool(paper.venue and prior.venue and paper.venue.casefold() != prior.venue.casefold()) or
                        bool(paper.authors and prior.authors and paper.authors != prior.authors))
            return ('conflict' if conflict else 'duplicate'), None, (
                'Conflicting metadata for a DOI in this batch' if conflict else 'Duplicate of an earlier record in this batch'), None, prior_index
        if paper.title_hash == prior.title_hash:
            if paper.doi and prior.doi and paper.doi != prior.doi:
                return 'conflict', None, 'Same title has different DOIs in this batch', None, prior_index
            if not paper.doi or not prior.doi:
                return 'conflict', None, 'Title-only identity is ambiguous within this batch', None, prior_index
    return 'new', None, 'New bibliography record', None, None


def _preview(store, files):
    deadline = time.monotonic() + MAX_SECONDS
    validated = _validated_files(files)
    items, internals, earlier = [], {}, []
    for file in validated:
        try:
            records = _parse(file, deadline)
            if not isinstance(records, list) or not 1 <= len(records) <= MAX_RECORDS:
                raise ValueError('Record bounds')
            if len(_json(records).encode('utf-8')) > MAX_PARSED_BYTES:
                raise ValueError('Parsed size bounds')
        except ImportValidationError:
            raise
        except (ValueError, UnicodeError, RuntimeError, subprocess.TimeoutExpired, OSError, RecursionError):
            if len(items) >= MAX_RECORDS:
                raise ImportValidationError('Import exceeds 500 records')
            items.append({'index': len(items), 'filename': file['filename'], 'record_key': '', 'status': 'failed',
                          'paper_id': None, 'title': '', 'message': 'Invalid/unsupported file, missing optional parser, or parser bounds exceeded',
                          'metadata': {}, 'message_code': 'invalid_file'})
            continue
        for record in records:
            if len(items) >= MAX_RECORDS or time.monotonic() >= deadline:
                raise ImportValidationError('Import exceeds 500 records or 30-second preview bounds')
            index = len(items)
            item = {'index': index, 'filename': file['filename'], 'record_key': str(record.get('key', ''))[:100] if isinstance(record, dict) else '',
                    'status': 'failed', 'paper_id': None, 'title': '', 'message': 'Invalid bibliographic metadata', 'message_code': 'invalid_metadata', 'metadata': {}}
            try:
                paper = _paper(record, file)
                if paper is None:
                    item.update(status='skipped', message_code='missing_title', message='No usable title; PDF text/OCR and filename inference are not supported')
                else:
                    status, paper_id, message, fingerprint, duplicate_of = _classify(store, paper, earlier)
                    metadata = asdict(paper)
                    item.update(status=status, paper_id=paper_id, title=paper.title, message=message,
                                metadata=metadata, message_code={'new': 'new', 'duplicate': 'duplicate', 'conflict': 'conflicting_metadata'}[status], confidence='low' if file['format'] == 'pdf' else 'declared')
                    if duplicate_of is not None:
                        item['duplicate_of'] = duplicate_of
                    internals[index] = {'paper': paper, 'fingerprint': fingerprint}
                    if status == 'new':
                        earlier.append((index, paper))
            except (ValueError, TypeError, AttributeError, OverflowError):
                pass
            items.append(item)
    if len(_json(items).encode('utf-8')) > MAX_PARSED_BYTES:
        raise ImportValidationError('Preview metadata exceeds 2 MB')
    counts = {status: sum(item['status'] == status for item in items) for status in STATUSES}
    fingerprints = {str(index): value['fingerprint'] for index, value in internals.items()}
    scope = {'database': str(store.path.absolute()), 'files': [(f['filename'], f['format'], f['sha256']) for f in validated],
             'items': items, 'targets': fingerprints, 'version': PARSER_VERSION}
    return {'token': _digest(scope), 'items': items, 'counts': counts,
            'metadata_only': True, 'limits': {'files': MAX_FILES, 'total_bytes': MAX_TOTAL_BYTES, 'records': MAX_RECORDS}}, internals


def preview_import(store: PaperStore, files: list[dict]) -> dict:
    """Read and classify uploaded bytes; never writes preview data."""
    return _preview(store, files)[0]


def commit_import(store: PaperStore, files: list[dict], token: str, selected_indices=None) -> dict:
    if not isinstance(token, str) or not re.fullmatch(r'[a-f0-9]{64}', token):
        raise ImportValidationError('Use the token from a current import preview')
    if store.conn.in_transaction:
        raise ImportValidationError('Finish the current transaction before import')
    store.conn.execute('BEGIN IMMEDIATE')
    try:
        plan, internals = _preview(store, files)
        if token != plan['token']:
            raise StaleImportError('Files or matching library records changed; preview again')
        actionable = {item['index'] for item in plan['items'] if item['status'] in {'new', 'duplicate'}}
        if selected_indices is None:
            selected = actionable
        else:
            if (not isinstance(selected_indices, list) or not selected_indices or
                    any(type(index) is not int for index in selected_indices) or
                    len(selected_indices) != len(set(selected_indices))):
                raise ImportValidationError('Select distinct new/duplicate record indices')
            selected = set(selected_indices)
            if not selected <= actionable:
                raise ImportValidationError('Only new/duplicate preview records may be selected')
        if not selected:
            raise ImportValidationError('No importable records selected')
        batch_id, now = uuid.uuid4().hex, datetime.now(timezone.utc).isoformat()
        store.conn.execute('INSERT INTO local_import_batches VALUES (?, ?, ?, ?, ?, ?)',
                           (batch_id, now, token, len(selected), 0, 0))
        added, duplicates, observations, paper_ids = 0, 0, 0, []
        for index in sorted(selected):
            paper = internals[index]['paper']
            # Reuse canonical dedup, but never call overwrite-prone upsert for
            # existing papers. All duplicates only gain a separate observation.
            paper_id = plan['items'][index]['paper_id']
            if paper_id is None:
                paper_id = store.find_existing_paper_id(paper)
            if paper_id is None:
                paper_id = store._upsert_paper_no_commit(paper, relevance_score=0, matched_groups={},
                                                        scoring_version='local-import-unranked')
                added += 1
            else:
                duplicates += 1
            key = paper.external_id
            cursor = store.conn.execute('INSERT OR IGNORE INTO local_import_observations '
                '(observation_key,paper_id,batch_id,filename,format,file_sha256,record_key,metadata_json,created_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (key, paper_id, batch_id, paper.raw['filename'], paper.raw['format'], paper.raw['file_sha256'],
                 paper.raw['record_key'], _json(asdict(paper)), now))
            observations += cursor.rowcount
            paper_ids.append(paper_id)
        store.conn.execute('UPDATE local_import_batches SET added_count=?,duplicate_count=? WHERE batch_id=?',
                           (added, duplicates, batch_id))
        store.conn.commit()
        return {'batch_id': batch_id, 'added': added, 'duplicates': duplicates,
                'observations_added': observations, 'paper_ids': list(dict.fromkeys(paper_ids))}
    except Exception:
        store.conn.rollback()
        raise


def list_batches(store: PaperStore, limit: int = 20) -> list[dict]:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ImportValidationError('Batch limit must be 1–100')
    return [dict(row) for row in store.conn.execute(
        'SELECT * FROM local_import_batches ORDER BY created_at DESC,batch_id DESC LIMIT ?', (limit,))]
