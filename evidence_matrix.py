"""Deterministic metadata/evidence exports without inference or personal notes."""
from __future__ import annotations

import csv
import html
import io
import json
import re
from typing import Iterable

from storage.evidence import EvidenceStore, FIELD_NAMES

MAX_EXPORT_PAPERS = 200


def _records(store, paper_ids: Iterable[int]):
    # Consume at most the bounded batch, even when given an infinite iterator.
    ids = []
    for value in paper_ids:
        if len(ids) >= MAX_EXPORT_PAPERS:
            raise ValueError('Evidence export is limited to 200 paper IDs')
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError('Paper IDs must be positive integers')
        ids.append(value)
    evidence = EvidenceStore(store)
    records = []
    for paper_id in sorted(set(ids)):
        worksheet = evidence.get(paper_id)
        observations = [json.loads(row['observation_json']) for row in store.conn.execute(
            'SELECT observation_json FROM paper_venue_observations WHERE paper_id=? ORDER BY source_id',
            (paper_id,))]
        worksheet['venue_observations'] = observations
        venue_types = {item.get('venue', {}).get('venue_type', 'unknown') for item in observations}
        field = worksheet['fields']['venue_type']
        if field['origin'] == 'unknown' and field['value'] == 'unknown' and len(venue_types) == 1:
            field.update(value=next(iter(venue_types)), origin='imported_metadata',
                         source_ref='; '.join(item.get('venue', {}).get('record_url', '') for item in observations),
                         source_type='OpenAlex source metadata',
                         recorded_at='; '.join(item.get('venue', {}).get('retrieved_at', '') for item in observations))
        records.append((dict(store.get(paper_id)), worksheet))
    return records


def _md(value: object) -> str:
    text = html.escape(str(value), quote=True)
    text = text.replace('\\', '\\\\')
    text = re.sub(r'([`*_{}\[\]()#+.!|~-])', r'\\\1', text)
    return text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>')


def _value(evidence, name):
    return evidence['fields'][name]['value'] or 'not verified'


def _metadata(paper, evidence):
    refs = json.loads(paper.get('source_refs_json') or '{}')
    return {'paper_id': paper['id'], 'title': paper['title'],
            'authors': '; '.join(json.loads(paper['authors_json'] or '[]')),
            'year': (paper.get('published_at') or '')[:4] or 'unknown',
            'doi': paper.get('doi') or 'unknown', 'url': paper.get('url') or 'unknown',
            'sources': '; '.join(sorted({paper['source'], *refs.keys()})),
            'venue': paper.get('venue') or 'unknown',
            'venue_observations': json.dumps(evidence['venue_observations'], ensure_ascii=False, sort_keys=True)}


def export_markdown(store, paper_ids, *, research_question='', hypothesis='', disconfirming_evidence='') -> str:
    records = _records(store, paper_ids)
    lines = ['# Literature evidence worksheet', '',
             'Metadata is provider-reported. Missing findings are not verified. Gap candidates are unverified working hypotheses; this export does not certify novelty, peer review or indexing.', '',
             '## Research question', '', _md(research_question or 'not specified'), '',
             '## Comparison hypothesis', '', _md(hypothesis or 'not specified'), '',
             '## Disconfirming evidence', '', _md(disconfirming_evidence or 'not verified'), '',
             '| Paper (year, venue) | Task/data | Context used | Selection mechanism | Baselines/evidence | Limitations (author-stated) | My hypothesis / possible gap | Evidence quality |',
             '| --- | --- | --- | --- | --- | --- | --- | --- |']
    for paper, evidence in records:
        m = _metadata(paper, evidence)
        cells = [f"#{m['paper_id']}: {m['title']} ({m['year']}, {m['venue']})",
                 _value(evidence, 'task_scope') + '; datasets: ' + _value(evidence, 'datasets'),
                 _value(evidence, 'data_context'), _value(evidence, 'context_selection'),
                 _value(evidence, 'baselines') + '; outcome: ' + _value(evidence, 'reported_outcome'),
                 _value(evidence, 'author_limitations'), _value(evidence, 'gap_candidate'),
                 _value(evidence, 'evidence_granularity')]
        lines.append('| ' + ' | '.join(_md(c) for c in cells) + ' |')
    for paper, evidence in records:
        m = _metadata(paper, evidence)
        lines.extend(['', f"## Evidence card: paper #{m['paper_id']}", ''])
        for name, value in m.items():
            lines.append(f'- **{name} (provider metadata):** {_md(value)}')
        lines.extend([f"- **Worksheet revision:** {evidence['revision']}",
                      '- **Gap candidate status:** unverified', '',
                      '| Field | Statement | Origin | Source / location | Reviewed / recorded | Verification |',
                      '| --- | --- | --- | --- | --- | --- |'])
        for name in FIELD_NAMES:
            item = evidence['fields'][name]
            cells = [name, item['value'] or 'not verified', item['origin'],
                     f"{item['source_ref'] or 'not specified'}; {item['source_type'] or 'unknown'}; {item['location'] or 'not specified'}",
                     f"{item['reviewed_at'] or 'not specified'}; {item['recorded_at'] or 'not specified'}",
                     item['verification_status']]
            lines.append('| ' + ' | '.join(_md(c) for c in cells) + ' |')
    return '\n'.join(lines) + '\n'


def _csv_cell(value):
    # Prevent spreadsheet formula interpretation of untrusted metadata/text.
    text = str(value)
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')) else text


def export_csv(store, paper_ids) -> str:
    records = _records(store, paper_ids)
    columns = ['paper_id', 'title', 'authors', 'year', 'doi', 'url', 'sources', 'venue', 'venue_observations', 'revision', 'gap_candidate_status']
    for name in FIELD_NAMES:
        columns.extend(f'{name}.{key}' for key in ('value', 'origin', 'source_ref', 'source_type', 'location', 'reviewed_at', 'recorded_at', 'verification_status'))
    output = io.StringIO(newline='')
    writer = csv.writer(output, lineterminator='\n')
    writer.writerow(columns)
    for paper, evidence in records:
        m = _metadata(paper, evidence)
        values = [m[name] for name in columns[:9]] + [evidence['revision'], 'unverified']
        for name in FIELD_NAMES:
            values.extend(evidence['fields'][name][key] for key in ('value', 'origin', 'source_ref', 'source_type', 'location', 'reviewed_at', 'recorded_at', 'verification_status'))
        writer.writerow([_csv_cell(v) for v in values])
    return output.getvalue()
