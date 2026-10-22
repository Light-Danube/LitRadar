"""Bounded bibliography parser worker. Reads bytes from stdin, never paths/URLs."""
from __future__ import annotations

import io
import json
import re
import sys

MAX_RECORDS = 500
MAX_OUTPUT_BYTES = 2_000_000


def parse_ris(text: str) -> list[dict]:
    records, fields, last = [], None, None
    for line in text.splitlines():
        if len(line) > 20000:
            raise ValueError('RIS field bounds')
        if not line.strip():
            continue
        match = re.fullmatch(r'([A-Z0-9]{2})\s+-\s?(.*)', line)
        if not match:
            if fields is None or last is None:
                raise ValueError('Malformed RIS')
            if len(fields[last][-1]) + len(line) > 20000:
                raise ValueError('RIS field bounds')
            fields[last][-1] += '\n' + line.strip()
            continue
        tag, value = match.groups()
        if tag == 'TY':
            if fields is not None:
                raise ValueError('Unclosed RIS')
            fields, last = {'TY': [value]}, tag
        elif tag == 'ER':
            if fields is None:
                raise ValueError('Unexpected RIS end')
            records.append({'key': str(len(records) + 1), 'fields': fields})
            fields, last = None, None
        else:
            if fields is None:
                raise ValueError('RIS field outside record')
            fields.setdefault(tag, []).append(value)
            last = tag
        if len(records) > MAX_RECORDS:
            raise ValueError('Too many records')
    if fields is not None or not records:
        raise ValueError('Incomplete RIS')
    return records


def parse_bibtex(text: str) -> list[dict]:
    from bibtexparser.bparser import BibTexParser
    parser = BibTexParser(common_strings=True)
    database = parser.parse(text, partial=False)
    if not database.entries or len(database.entries) > MAX_RECORDS:
        raise ValueError('Invalid bibliography size')
    return [{'key': str(index + 1), 'fields': {str(k): [str(v)] for k, v in entry.items()}}
            for index, entry in enumerate(database.entries)]


def parse_pdf(data: bytes) -> list[dict]:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted:
        raise ValueError('Encrypted PDF')
    if not 1 <= len(reader.pages) <= 50:
        raise ValueError('PDF page limit')
    info = reader.metadata or {}
    # No page extraction: PDF Info metadata is not authoritative bibliographic
    # identification, and missing titles are never fabricated from a filename.
    title = str(info.get('/Title') or '').strip()
    if len(title) < 3 or title.casefold() in {'untitled', 'document', 'microsoft word'}:
        return [{'key': '1', 'fields': {}, 'pdf_metadata_only': True}]
    author = str(info.get('/Author') or '').strip()
    return [{'key': '1', 'fields': {'title': [title], 'author': [author]},
             'pdf_metadata_only': True}]


if __name__ == '__main__':
    try:
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
            resource.setrlimit(resource.RLIMIT_CPU, (8, 8))
        except ImportError:
            pass  # Parent-enforced timeout and byte/page caps still apply.
        content = sys.stdin.buffer.read(5_000_001)
        if not content or len(content) > 5_000_000:
            raise ValueError('Input bounds')
        kind = sys.argv[1]
        records = parse_pdf(content) if kind == 'pdf' else parse_bibtex(content.decode('utf-8-sig'))
        output = json.dumps(records, ensure_ascii=False).encode('utf-8')
        if len(output) > MAX_OUTPUT_BYTES:
            raise ValueError('Output bounds')
        sys.stdout.buffer.write(output)
    except Exception:
        print('Invalid or unsupported bibliography, or parser bounds exceeded', file=sys.stderr)
        sys.exit(1)
