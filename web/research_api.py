"""Explicit local research actions; no background retrieval or inference."""
from contextlib import contextmanager
import json
import sqlite3
from pathlib import Path
import urllib.error

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse

from config import RadarConfig
from evidence_matrix import export_csv, export_markdown
from sources import venues
from storage.evidence import EvidenceStore
from storage.sqlite import PaperStore
import venue_discovery
from .research_files import ResearchFiles, FileConflict, FileValidationError

MAX_BODY = 150_000


async def _body(request: Request):
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_BODY:
            raise HTTPException(413, {'status': 'invalid_request', 'message': 'Research request is too large'})
        raw.extend(chunk)
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise HTTPException(422, {'status': 'invalid_request', 'message': 'Invalid JSON object'}) from exc
    if not isinstance(payload, dict):
        raise HTTPException(422, {'status': 'invalid_request', 'message': 'Expected JSON object'})
    return payload


def _keys(payload, allowed, required=()):
    if payload.keys() - set(allowed) or set(required) - payload.keys():
        raise ValueError('Unsupported or missing request fields')


def _integer(value, name, low=0, high=100):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f'{name} must be an integer between {low} and {high}')
    return value


@contextmanager
def _store(db_path):
    store = PaperStore(db_path)
    try:
        yield store
    finally:
        store.close()


@contextmanager
def _errors():
    try:
        yield
    except HTTPException:
        raise
    except KeyError as exc:
        raise HTTPException(404, {'status': 'not_found', 'message': 'Research record not found'}) from exc
    except FileConflict as exc:
        raise HTTPException(409, {'status': 'conflict', 'message': str(exc)}) from exc
    except (urllib.error.URLError, TimeoutError, venues.VenueMetadataError) as exc:
        status = venue_discovery.error_status(exc)
        raise HTTPException(502, {'status': status, 'message': 'Discovery provider request failed; retry or inspect local configuration'}) from exc
    except ValueError as exc:
        conflict = 'changed' in str(exc).lower()
        raise HTTPException(409 if conflict else 422, {'status': 'conflict' if conflict else 'invalid_request', 'message': str(exc)}) from exc
    except (OSError, sqlite3.Error) as exc:
        raise HTTPException(503, {'status': 'save_failed', 'message': 'Local research storage is unavailable'}) from exc


def _saved(reserved, kind, files, metadata, *, saved_in_database=False):
    try:
        return reserved.save(kind, files, metadata)
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        raise HTTPException(503, {'status': 'save_failed', 'message': 'Research snapshot could not be saved; reload database state before retrying an edit',
                                  'saved_in_database': saved_in_database}) from exc


def register_research_routes(app, db_path, results_root=None):
    files = ResearchFiles(results_root if results_root is not None else Path(db_path).parent / 'research')

    @app.post('/api/research/venues/lookup')
    def lookup(payload=Depends(_body)):
        with _errors():
            _keys(payload, {'query', 'limit'}, {'query'})
            query = payload['query']
            if not isinstance(query, str) or not query.strip() or len(query) > 500:
                raise ValueError('Query must contain 1–500 characters')
            limit = _integer(payload.get('limit', 10), 'limit', 1, 100)
            with _store(db_path) as store:
                try:
                    found = venue_discovery.lookup(store, query, limit=limit, config=RadarConfig.load())
                except OSError as exc:
                    raise HTTPException(502, {'status':venue_discovery.error_status(exc), 'message':'Discovery provider request failed'}) from exc
            return {'status': 'ambiguous_venue' if len(found) > 1 else 'ok' if found else 'zero_results', 'venues': [item.to_dict() for item in found],
                    'next_step': 'Select a concrete source identity before searching'}

    @app.post('/api/research/search')
    def search(payload=Depends(_body)):
        with _errors():
            _keys(payload, {'source_id','query','year_from','year_to','limit','page','refresh','identifier'}, {'source_id','query'})
            if not isinstance(payload['source_id'], str) or len(payload['source_id']) > 100:
                raise ValueError('Source ID must contain at most 100 characters')
            query, source_id = venues.validate_search(payload['query'], payload['source_id'],
                year_from=payload.get('year_from'), year_to=payload.get('year_to'),
                limit=payload.get('limit',20), page=payload.get('page',1))
            if len(query) > 500:
                raise ValueError('Query must contain 1–500 characters')
            _integer(payload.get('page',1), 'page', 1, 10)
            for name in ('year_from','year_to'):
                if payload.get(name) is not None:
                    _integer(payload[name], name, 1000, 9999)
            if not isinstance(payload.get('refresh', False), bool):
                raise ValueError('refresh must be a boolean')
            with files.reserve(payload.get('identifier')) as reserved:
                with _store(db_path) as store:
                    try:
                        result = venue_discovery.search_and_store(store, query, source_id,
                        year_from=payload.get('year_from'), year_to=payload.get('year_to'),
                        limit=payload.get('limit',20), page=payload.get('page',1),
                            force=payload.get('refresh',False), config=RadarConfig.load())
                    except OSError as exc:
                        raise HTTPException(502, {'status':venue_discovery.error_status(exc), 'message':'Discovery provider request failed'}) from exc
                result['artifact'] = _saved(reserved, 'venue_search', {'search.json':result},
                    {'source_id':source_id,'query':query,'paper_ids':result['paper_ids'],'status':result['status']}, saved_in_database=True)
                return result

    @app.get('/api/papers/{paper_id}/evidence')
    def evidence_get(paper_id: int):
        with _errors(), _store(db_path) as store:
            return EvidenceStore(store).get(paper_id)

    @app.patch('/api/papers/{paper_id}/evidence')
    def evidence_update(paper_id: int, payload=Depends(_body)):
        with _errors():
            _keys(payload, {'fields','expected_revision'}, {'fields','expected_revision'})
            _integer(payload['expected_revision'],'expected_revision',0,2**31-1)
            with files.reserve() as reserved, _store(db_path) as store:
                result = EvidenceStore(store).update(paper_id, payload['fields'], payload['expected_revision'])
                result['artifact'] = _saved(reserved, 'evidence_snapshot', {'evidence.json':result},
                    {'paper_ids':[paper_id],'revision':result['revision']}, saved_in_database=True)
                return result

    @app.get('/api/research/presets')
    def presets_list():
        from storage.venue_presets import VenuePresetStore
        with _errors(), _store(db_path) as store:
            return {'items': VenuePresetStore(store).list()}

    @app.post('/api/research/presets')
    def presets_create(payload=Depends(_body)):
        from storage.venue_presets import VenuePresetStore
        with _errors(), _store(db_path) as store:
            return VenuePresetStore(store).create(payload)

    @app.put('/api/research/presets/{preset_id}')
    def presets_update(preset_id: int, payload=Depends(_body)):
        from storage.venue_presets import VenuePresetStore
        with _errors(), _store(db_path) as store:
            _keys(payload, {'fields','expected_revision'}, {'fields','expected_revision'})
            return VenuePresetStore(store).update(preset_id, payload['fields'],payload['expected_revision'])

    @app.delete('/api/research/presets/{preset_id}')
    def presets_delete(preset_id: int, expected_revision: int = Query(..., ge=0)):
        from storage.venue_presets import VenuePresetStore
        with _errors(), _store(db_path) as store:
            VenuePresetStore(store).delete(preset_id, expected_revision)
            return {'ok':True}

    @app.post('/api/research/exports')
    def exports(payload=Depends(_body)):
        with _errors():
            _keys(payload, {'paper_ids','identifier','research_question','hypothesis','disconfirming_evidence'}, {'paper_ids'})
            ids = payload['paper_ids']
            if not isinstance(ids,list) or not 1 <= len(ids) <= 100:
                raise ValueError('Select 1–100 paper IDs')
            for value in ids:
                _integer(value,'paper_id',1,2**63-1)
            context = {name:payload.get(name,'') for name in ('research_question','hypothesis','disconfirming_evidence')}
            if any(not isinstance(value,str) or len(value)>8000 for value in context.values()):
                raise ValueError('Export context must contain bounded text')
            with files.reserve(payload.get('identifier')) as reserved, _store(db_path) as store:
                return _saved(reserved,'evidence_export',{'matrix.md':export_markdown(store,ids,**context),
                    'matrix.csv':export_csv(store,ids)}, {'paper_ids':sorted(set(ids))})

    @app.get('/api/research/artifacts')
    def artifacts(limit: int = Query(20,ge=1,le=100)):
        with _errors():
            return {'items':files.list(limit)}

    @app.get('/api/research/artifacts/{identifier}/{filename}')
    def download(identifier: str, filename: str):
        with _errors():
            try:
                path = files.path(identifier,filename)
            except FileNotFoundError as exc:
                raise HTTPException(404, {'status':'not_found','message':'Research artifact not found'}) from exc
            return FileResponse(path,filename=filename,media_type='application/octet-stream',headers={'X-Content-Type-Options':'nosniff'})
