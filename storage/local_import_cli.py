"""Explicit preview and confirmation for user-selected local bibliography."""
from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path
import sqlite3
import sys

from .sqlite import PaperStore, SCHEMA


def _preview_store(database):
    """Migrate a disposable memory copy, never the previewed user's database."""
    target = Path(database).absolute()
    store = PaperStore(':memory:')
    try:
        if target.exists():
            with closing(sqlite3.connect(target.as_uri() + '?mode=ro', uri=True)) as source:
                source.backup(store.conn)
            store.conn.executescript(SCHEMA)
            store._migrate()
        store.path = target
        return store
    except Exception:
        store.close()
        raise


def cmd_import_papers(args):
    from .local_import import preview_import, commit_import, StaleImportError, ImportValidationError
    from .local_import_paths import read_selected_files, LocalPathError
    store = None
    try:
        if args.commit and not args.preview_token:
            raise LocalPathError('Commit requires the token from a reviewed preview')
        if not args.commit and (args.preview_token or args.select is not None):
            raise LocalPathError('Use --commit with --preview-token and optional --select')
        files = read_selected_files(args.root, args.files)
        store = PaperStore(args.db) if args.commit else _preview_store(args.db)
        result = (commit_import(store, files, args.preview_token, selected_indices=args.select)
                  if args.commit else preview_import(store, files))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except StaleImportError:
        print('Import preview is stale. Preview the same selection again before importing.', file=sys.stderr)
        return 2
    except (ImportValidationError, LocalPathError) as exc:
        # These exceptions contain fixed user-facing messages, never parser text.
        print(f'Local import: {exc}', file=sys.stderr)
        return 2
    except (OSError, sqlite3.Error, ValueError):
        print('Local import failed. Check selected files and database access; no partial batch was saved.', file=sys.stderr)
        return 1
    finally:
        if store is not None:
            store.close()


def register_commands(sub):
    parser = sub.add_parser('import-papers', help='preview/import local RIS, BibTeX or PDF metadata as papers (offline)',
                            description='Select individual files beneath an explicit root. Preview is the default; '
                                        'commit requires its token. Originals are never moved or changed. '
                                        'This creates bibliography records, separately from annotation import.')
    parser.add_argument('files', nargs='+', help='individual filenames relative to --root; no directory scan')
    parser.add_argument('--root', required=True, help='explicit input directory; linked paths are rejected')
    parser.add_argument('--commit', action='store_true', help='confirm a reviewed preview')
    parser.add_argument('--preview-token', help='token from the preview of the same files and database')
    parser.add_argument('--select', type=int, nargs='+', help='optional zero-based preview row indices to import')
    parser.set_defaults(func=cmd_import_papers)
