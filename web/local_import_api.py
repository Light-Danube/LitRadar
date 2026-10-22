"""Bounded, explicit uploaded-byte bibliography import into the local library."""
from __future__ import annotations

import base64
import binascii
import json
import sqlite3

from fastapi import HTTPException, Request
from starlette.concurrency import run_in_threadpool

from storage.sqlite import PaperStore
from storage.local_import_cli import _preview_store

MAX_BODY = 14_000_000
MAX_FILES = 10
MAX_FILE_BYTES = 5_000_000
MAX_TOTAL_BYTES = 10_000_000


def _error(code, status, message):
    return HTTPException(code, {'status': status, 'message': message})


async def _body(request: Request) -> dict:
    if request.headers.get('content-type', '').split(';', 1)[0].strip().lower() != 'application/json':
        raise _error(415, 'import_invalid', 'Local import requires a JSON request')
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_BODY:
            raise _error(413, 'import_invalid', 'Selected files exceed the upload limit')
        raw.extend(chunk)
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise _error(422, 'import_invalid', 'Invalid local import request') from exc
    if not isinstance(payload, dict):
        raise _error(422, 'import_invalid', 'Invalid local import request')
    return payload


def _files(payload: dict, *, commit: bool) -> list[dict]:
    allowed = {'files', 'token', 'selected_indices'} if commit else {'files'}
    if payload.keys() - allowed or 'files' not in payload:
        raise ValueError('invalid request')
    items = payload['files']
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_FILES:
        raise ValueError('invalid file count')
    files, total = [], 0
    for item in items:
        if not isinstance(item, dict) or set(item) != {'filename', 'format', 'content_base64'}:
            raise ValueError('invalid file')
        filename, kind, encoded = item['filename'], item['format'], item['content_base64']
        if not isinstance(filename, str) or not 1 <= len(filename) <= 250 or any(ord(c) < 32 for c in filename):
            raise ValueError('invalid filename')
        # Display labels only; uploaded filenames never become server paths.
        filename = filename.replace('\\', '/').rsplit('/', 1)[-1]
        if not filename or filename in {'.', '..'} or ':' in filename:
            raise ValueError('invalid filename')
        if kind not in ('ris', 'bibtex', 'pdf') or not isinstance(kind, str):
            raise ValueError('invalid format')
        if not isinstance(encoded, str) or not 1 <= len(encoded) <= 6_666_668:
            raise ValueError('invalid content')
        try:
            content = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError('invalid base64') from exc
        total += len(content)
        if not content or len(content) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            raise ValueError('invalid size')
        files.append({'filename': filename, 'format': kind, 'content': content})
    if commit:
        token = payload.get('token')
        if not isinstance(token, str) or len(token) != 64 or any(c not in '0123456789abcdef' for c in token):
            raise ValueError('invalid preview token')
        selected = payload.get('selected_indices')
        if not isinstance(selected, list) or not 1 <= len(selected) <= 500:
            raise ValueError('select records')
        if any(type(index) is not int or not 0 <= index < 500 for index in selected) or len(set(selected)) != len(selected):
            raise ValueError('invalid selection')
    return files


def _execute(db_path, files, payload, commit):
    from storage.local_import import preview_import, commit_import, ImportValidationError, StaleImportError
    store = None
    try:
        store = PaperStore(db_path) if commit else _preview_store(db_path)
        if commit:
            return commit_import(store, files, payload['token'], selected_indices=payload['selected_indices'])
        return preview_import(store, files)
    except StaleImportError as exc:
        raise _error(409, 'import_stale', 'The files or library changed. Preview again before importing') from exc
    except (ImportValidationError, ValueError, TypeError, KeyError) as exc:
        raise _error(422, 'import_invalid', 'Import could not be validated. Check the selected files and preview again') from exc
    except (RuntimeError, ImportError) as exc:
        raise _error(503, 'import_parser', 'An optional file parser is unavailable or could not finish. Check annotation parser dependencies') from exc
    except (OSError, sqlite3.Error) as exc:
        raise _error(503, 'import_storage', 'Local import storage is unavailable. Check the library and try again') from exc
    finally:
        if store is not None:
            store.close()


def register_local_import_routes(app, db_path):
    async def handle(request: Request, commit: bool):
        payload = await _body(request)
        try:
            files = _files(payload, commit=commit)
        except (ValueError, TypeError) as exc:
            raise _error(422, 'import_invalid', 'Invalid local import request. Select up to 10 files, 5 MB per file and 10 MB total') from exc
        return await run_in_threadpool(_execute, db_path, files, payload, commit)

    @app.post('/api/local-import/preview')
    async def preview(request: Request):
        return await handle(request, False)

    @app.post('/api/local-import/commit')
    async def commit(request: Request):
        return await handle(request, True)
