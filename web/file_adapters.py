"""Parse uploaded bytes only. PDF/BibTeX workers never follow file/URL references."""
import io
import json
import re
import sys


def parse_ris(text):
    entries, current, last = [], None, None
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.match(r'^([A-Z0-9]{2})\s+-\s?(.*)$', line)
        if not match:
            if current is None or last is None:
                raise ValueError('Invalid RIS record')
            current[last][-1] += '\n' + line.strip()
            continue
        tag, value = match.groups()
        if tag == 'TY':
            if current is not None:
                raise ValueError('Unclosed RIS record')
            current, last = {'TY': [value]}, tag
        elif tag == 'ER':
            if current is None:
                raise ValueError('RIS end without a record')
            entries.append({'content': json.dumps(current, ensure_ascii=False), 'source_ref': f'record {len(entries)+1}'})
            current, last = None, None
        else:
            if current is None:
                raise ValueError('RIS field outside a record')
            current.setdefault(tag, []).append(value)
            last = tag
        if len(entries) > 100:
            raise ValueError('At most 100 annotation records per import')
    if current is not None or not entries:
        raise ValueError('RIS requires complete TY/ER records')
    return entries


def parse_bibtex(text):
    from bibtexparser.bparser import BibTexParser
    parser = BibTexParser(common_strings=True)
    # parse_all avoids silently importing only a valid prefix of a malformed file.
    database = parser.parse(text, partial=False)
    if not database.entries:
        raise ValueError('BibTeX contains no reference records')
    return [{'content': json.dumps(entry, ensure_ascii=False), 'source_ref': entry.get('ID', f'record {i+1}')}
            for i, entry in enumerate(database.entries)]


def parse_pdf(data):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted:
        raise ValueError('Encrypted PDFs are not supported')
    if len(reader.pages) > 50:
        raise ValueError('PDF limit is 50 pages; import selected excerpts as JSON')
    entries = []
    for number, page in enumerate(reader.pages, 1):
        for reference in page.get('/Annots', []):
            annotation = reference.get_object()
            content = str(annotation.get('/Contents') or '').strip()
            if content:
                entries.append({'content': content, 'source_ref': f'page {number}; PDF comment'})
        text = page.extract_text() or ''
        if text.strip():
            entries.append({'content': text[:10000], 'source_ref': f'page {number}; text excerpt (max 10000 characters)'})
        if len(entries) > 100:
            raise ValueError('At most 100 annotation records per import')
    if not entries:
        raise ValueError('PDF has no extractable text/comments; OCR is not included')
    return entries


def bounded_entries(entries):
    if not 1 <= len(entries) <= 100:
        raise ValueError('Import requires 1–100 annotation records')
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) - {'content', 'source_ref'}:
            raise ValueError('Use content and optional source_ref only')
        content = entry.get('content')
        if not isinstance(content, str) or not content.strip() or len(content) > 50000:
            raise ValueError('Annotation content must contain 1–50000 characters')
        source = entry.get('source_ref')
        if source is not None and (not isinstance(source, str) or len(source) > 1700):
            raise ValueError('Source reference must be text of at most 1700 characters')
    if len(json.dumps(entries, ensure_ascii=False).encode('utf-8')) > 1000000:
        raise ValueError('Parsed annotation batch is too large')
    return entries


if __name__ == '__main__':
    # The subprocess bounds CPU/memory where POSIX supports them; it is not a general sandbox.
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (512*1024*1024, 512*1024*1024))
        resource.setrlimit(resource.RLIMIT_CPU, (12, 12))
    except ImportError:  # Windows retains the parent-enforced process timeout.
        pass
    try:
        data = sys.stdin.buffer.read(5000001)
        if len(data) > 5000000:
            raise ValueError('File is too large')
        entries = parse_pdf(data) if sys.argv[1] == 'pdf' else parse_bibtex(data.decode('utf-8-sig'))
        print(json.dumps(bounded_entries(entries), ensure_ascii=False))
    except Exception:
        # Never echo uploaded material or parser internals into the UI.
        print('Invalid or unsupported document, or parser resource limit exceeded', file=sys.stderr)
        sys.exit(1)
