"""Selected local paths never enumerate, redirect or alter original files."""
import os
from pathlib import Path

import pytest

from storage.local_import_paths import LocalPathError, read_selected_files


def test_unicode_selected_files_only(tmp_path, monkeypatch):
    folder = tmp_path / 'Дослідження'
    folder.mkdir()
    selected = folder / 'Праця.ris'
    selected.write_bytes(b'TY  - JOUR\nTI  - Science\nER  -\n')
    (folder / 'unselected.ris').write_bytes(b'PRIVATE')
    before = selected.read_bytes(), selected.stat().st_mtime_ns
    monkeypatch.setattr(Path, 'iterdir', lambda *a: pytest.fail('directory scan'))
    monkeypatch.setattr(Path, 'rglob', lambda *a: pytest.fail('recursive scan'))
    files = read_selected_files(tmp_path, ['Дослідження/Праця.ris'])
    assert files == [{'filename': 'Праця.ris', 'format': 'ris', 'content': before[0]}]
    assert (selected.read_bytes(), selected.stat().st_mtime_ns) == before


@pytest.mark.parametrize('name', ['../secret.ris', '/secret.ris', 'C:\\secret.ris',
    'a/../secret.ris', 'a//secret.ris', 'a:secret.ris', '\\\\host\\secret.ris',
    './secret.ris', 'archive.zip', 'bad\x00.ris'])
def test_invalid_selection(tmp_path, name):
    with pytest.raises(LocalPathError):
        read_selected_files(tmp_path, [name])


def test_network_root_rejected_before_access(monkeypatch):
    monkeypatch.setattr(Path, 'lstat', lambda *a: pytest.fail('network path access'))
    for root in ['//host/share', '\\\\host\\share']:
        with pytest.raises(LocalPathError, match='Network'):
            read_selected_files(root, ['paper.ris'])


@pytest.mark.skipif(os.name == 'nt', reason='POSIX links/FIFO contract; native Windows separate')
def test_links_directories_and_fifo_are_rejected(tmp_path):
    target = tmp_path / 'paper.ris'
    target.write_bytes(b'private')
    linked = tmp_path / 'linked.ris'
    linked.symlink_to(target)
    alias = tmp_path / 'alias'
    alias.symlink_to(tmp_path, target_is_directory=True)
    hard = tmp_path / 'hard.ris'
    os.link(target, hard)
    directory = tmp_path / 'directory.ris'
    directory.mkdir()
    fifo = tmp_path / 'fifo.ris'
    os.mkfifo(fifo)
    for name in [linked.name, hard.name, target.name, directory.name, fifo.name, 'alias/linked.ris']:
        with pytest.raises(LocalPathError):
            read_selected_files(tmp_path, [name])
    with pytest.raises(LocalPathError):
        read_selected_files(alias, ['paper.ris'])


def test_size_and_file_count_limits(tmp_path):
    path = tmp_path / 'large.ris'
    with path.open('wb') as stream:
        stream.truncate(5_000_001)
    with pytest.raises(LocalPathError):
        read_selected_files(tmp_path, [path.name])
    with pytest.raises(LocalPathError):
        read_selected_files(tmp_path, [path.name] * 11)


@pytest.mark.skipif(os.name == 'nt', reason='POSIX no-follow parent replacement')
def test_parent_replaced_by_symlink_cannot_redirect_open(tmp_path, monkeypatch):
    import storage.local_import_paths as paths
    selected = tmp_path / 'selected'
    selected.mkdir()
    (selected / 'paper.ris').write_bytes(b'original')
    other = tmp_path / 'other'
    other.mkdir()
    (other / 'paper.ris').write_bytes(b'PRIVATE SENTINEL')
    original_open = paths._posix_open
    def swap(root, relative):
        selected.rename(tmp_path / 'moved')
        selected.symlink_to(other, target_is_directory=True)
        return original_open(root, relative)
    monkeypatch.setattr(paths, '_posix_open', swap)
    with pytest.raises(LocalPathError):
        read_selected_files(tmp_path, ['selected/paper.ris'])
