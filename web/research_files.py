"""Immutable, bounded research snapshots; no arbitrary file or URL access."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import uuid

ALLOWED_FILES = {'manifest.json', 'search.json', 'evidence.json', 'matrix.md', 'matrix.csv'}
MAX_FILE_BYTES = 5_000_000
MAX_BUNDLE_BYTES = 12_000_000


class FileValidationError(ValueError):
    pass


class FileConflict(FileExistsError):
    pass


def _identifier(value):
    value = uuid.uuid4().hex if value is None else value
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
        raise FileValidationError('Identifier must contain 1–64 ASCII letters, digits, hyphens or underscores')
    if re.fullmatch(r'(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])', value, flags=re.IGNORECASE):
        raise FileValidationError('Windows reserved device identifiers are not allowed')
    return value


def _safe_tree(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink():
            raise FileValidationError('Symlink paths are not allowed')
    return path


class ResearchFiles:
    def __init__(self, root):
        self.root = Path(root).absolute()

    def _root(self):
        _safe_tree(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        return _safe_tree(self.root)

    @contextmanager
    def reserve(self, identifier=None):
        name = _identifier(identifier)
        root = self._root()
        target = root / name
        lock = root / f'.{name}.reserve'
        if os.path.lexists(target):
            raise FileConflict('Research identifier already exists')
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        except FileExistsError as exc:
            raise FileConflict('Research identifier is already reserved') from exc
        os.close(fd)
        try:
            if os.path.lexists(target):
                raise FileConflict('Research identifier already exists')
            yield _Reservation(self, name)
        finally:
            lock.unlink(missing_ok=True)

    def save(self, kind, files, identifier=None, metadata=None):
        with self.reserve(identifier) as reserved:
            return reserved.save(kind, files, metadata)

    def path(self, identifier, filename):
        name = _identifier(identifier)
        if filename not in ALLOWED_FILES:
            raise FileValidationError('Unsupported research filename')
        path = self.root / name / filename
        _safe_tree(path)
        if not path.is_file() or not (path.parent / 'manifest.json').is_file():
            raise FileNotFoundError('Research artifact not found')
        _safe_tree(path.parent / 'manifest.json')
        if path.stat().st_size > MAX_FILE_BYTES:
            raise FileValidationError('Research file exceeds download bound')
        return path

    def list(self, limit=20):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise FileValidationError('Limit must be 1–100')
        _safe_tree(self.root)
        if not self.root.exists():
            return []
        items = []
        # Cap metadata enumeration; never read user content files.
        for scanned, entry in enumerate(self.root.iterdir()):
            if scanned >= 1000:
                break
            if entry.name.startswith('.') or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', entry.name):
                continue
            try:
                path = self.path(entry.name, 'manifest.json')
                metadata = json.loads(path.read_text(encoding='utf-8'))
                if (isinstance(metadata, dict) and metadata.get('identifier') == entry.name
                        and isinstance(metadata.get('created_at'), str)
                        and isinstance(metadata.get('kind'), str)
                        and isinstance(metadata.get('metadata'), dict)
                        and metadata.get('relative_path') == f'research/{entry.name}'
                        and isinstance(metadata.get('files'), list)
                        and 1 <= len(metadata['files']) <= len(ALLOWED_FILES)
                        and all(isinstance(name, str) and name in ALLOWED_FILES for name in metadata['files'])
                        and 'manifest.json' in metadata['files']):
                    items.append(metadata)
            except (OSError, ValueError, RecursionError):
                continue
        return sorted(items, key=lambda item: (item.get('created_at', ''), item['identifier']), reverse=True)[:limit]


class _Reservation:
    def __init__(self, owner, identifier):
        self.owner, self.identifier = owner, identifier
        self.used = False

    def save(self, kind, files, metadata=None):
        if self.used:
            raise FileConflict('Research bundle is immutable')
        if not isinstance(kind, str) or len(kind) > 80:
            raise FileValidationError('Invalid artifact kind')
        if not isinstance(files, dict) or not files or files.keys() - (ALLOWED_FILES - {'manifest.json'}):
            raise FileValidationError('Unsupported research filenames')
        encoded = {}
        for name, value in files.items():
            content = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) if isinstance(value, dict) else value
            if not isinstance(content, str):
                raise FileValidationError('Research files must contain text or JSON objects')
            encoded[name] = content.encode('utf-8')
            if len(encoded[name]) > MAX_FILE_BYTES:
                raise FileValidationError('Research file exceeds size bound')
        artifact = {'identifier': self.identifier, 'relative_path': f'research/{self.identifier}',
                    'kind': kind, 'created_at': datetime.now(timezone.utc).isoformat(),
                    'files': sorted([*encoded, 'manifest.json']), 'metadata': metadata or {}}
        encoded['manifest.json'] = json.dumps(artifact, ensure_ascii=False, sort_keys=True, indent=2).encode('utf-8')
        if len(encoded['manifest.json']) > MAX_FILE_BYTES or sum(map(len, encoded.values())) > MAX_BUNDLE_BYTES:
            raise FileValidationError('Research bundle exceeds size bound')
        root = self.owner._root()
        stage = Path(tempfile.mkdtemp(prefix='.research-', dir=root))
        try:
            for name, content in encoded.items():
                descriptor = os.open(stage / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_BINARY', 0), 0o600)
                with os.fdopen(descriptor, 'wb') as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
            target = root / self.identifier
            if os.path.lexists(target):
                raise FileConflict('Research identifier already exists')
            os.rename(stage, target)
            self.used = True
            return artifact
        finally:
            if stage.exists():
                shutil.rmtree(stage)
