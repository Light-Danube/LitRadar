"""CLI roundtrip, readonly preview, recovery and old-reader compatibility."""
import argparse
import hashlib
import json
import sqlite3

from storage.local_import_cli import cmd_import_papers
from storage.recovery import backup_library, restore_library
from storage.sqlite import PaperStore


def args(tmp_path, **kwargs):
    values = dict(db=str(tmp_path / 'library.sqlite3'), root=str(tmp_path),
                  files=['Праця.ris'], commit=False, preview_token=None, select=None)
    values.update(kwargs)
    return argparse.Namespace(**values)


def test_cli_preview_creates_no_database_and_commit_is_searchable(tmp_path, capsys):
    file = tmp_path / 'Праця.ris'
    file.write_text('TY  - JOUR\nTI  - Українська наукова публікація\nDO  - 10.1234/local\nER  -\n', encoding='utf-8')
    original = file.read_bytes()
    assert cmd_import_papers(args(tmp_path)) == 0
    preview = json.loads(capsys.readouterr().out)
    assert not (tmp_path / 'library.sqlite3').exists()
    assert cmd_import_papers(args(tmp_path, commit=True, preview_token=preview['token'])) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['added'] == 1
    assert file.read_bytes() == original
    store = PaperStore(tmp_path / 'library.sqlite3')
    try:
        rows = store.conn.execute("SELECT rowid FROM papers_fts WHERE papers_fts MATCH ?", ('наукова',)).fetchall()
        assert rows[0][0] == result['paper_ids'][0]
        store.set_notes(result['paper_ids'][0], 'Retain notes')
    finally:
        store.close()
    before = hashlib.sha256((tmp_path / 'library.sqlite3').read_bytes()).hexdigest()
    assert cmd_import_papers(args(tmp_path)) == 0
    capsys.readouterr()
    assert hashlib.sha256((tmp_path / 'library.sqlite3').read_bytes()).hexdigest() == before
    bundle = tmp_path / 'snapshot'
    backup_library(tmp_path / 'library.sqlite3', bundle)
    restored = restore_library(bundle, tmp_path / 'restored')
    with sqlite3.connect(restored) as conn:
        assert conn.execute('SELECT notes FROM papers').fetchone()[0] == 'Retain notes'
        assert conn.execute('SELECT count(*) FROM local_import_batches').fetchone()[0] == 1
        assert conn.execute('SELECT count(*) FROM local_import_observations').fetchone()[0] == 1


def test_legacy_database_preview_and_missing_confirmation_do_not_write(tmp_path, capsys):
    database = tmp_path / 'library.sqlite3'
    store = PaperStore(database)
    store.conn.execute('DROP TABLE local_import_observations')
    store.conn.execute('DROP TABLE local_import_batches')
    store.conn.commit()
    store.close()
    (tmp_path / 'Праця.ris').write_text('TY  - JOUR\nTI  - Legacy import\nER  -\n')
    before = database.read_bytes()
    assert cmd_import_papers(args(tmp_path)) == 0
    token = json.loads(capsys.readouterr().out)['token']
    assert database.read_bytes() == before
    assert cmd_import_papers(args(tmp_path, commit=True)) == 2
    assert database.read_bytes() == before
    assert cmd_import_papers(args(tmp_path, commit=True, preview_token=token)) == 0
    capsys.readouterr()
