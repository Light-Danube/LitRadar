"""Package boundary contracts; real extracted-wheel install is verified in CI."""
from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts import build_user_bundle as bundle


@pytest.fixture
def wheel(tmp_path):
    version = (bundle.ROOT / 'VERSION').read_text().strip()
    path = tmp_path / f'litradar-{version}-py3-none-any.whl'
    with ZipFile(path, 'w') as archive:
        for name in bundle.REQUIRED:
            archive.writestr(name, version if name.endswith('/VERSION') else 'synthetic runtime fixture')
        archive.writestr(f'litradar-{version}.dist-info/METADATA', f'Name: litradar\nVersion: {version}\n')
    return path


def test_bundle_contains_only_identical_wheel_and_standalone_setup(wheel, tmp_path):
    artifact = bundle.build_bundle(wheel, tmp_path / 'output')
    with ZipFile(artifact) as archive:
        assert set(archive.namelist()) == {wheel.name, 'SETUP.txt'}
        assert archive.read(wheel.name) == wheel.read_bytes()
        text = archive.read('SETUP.txt').decode('utf-8')
        assert f'{wheel.name}[web]' in text
        assert 'python.exe -m cli web' in text and './.venv/bin/python -m cli web' in text
        assert 'library-backup' in text and '3.11+' in text
        assert 'py -3.12 -m venv .venv' in text
        assert 'py -3 -m venv .venv' not in text
        assert 'python.exe -m pip install --no-cache-dir' in text
        assert './.venv/bin/python -m pip install --no-cache-dir' in text
        assert 'Save this file and the wheel together' in text
        assert (bundle.ROOT / 'LICENSE').read_text(encoding='utf-8') in text
    original = artifact.read_bytes()
    with pytest.raises(FileExistsError):
        bundle.build_bundle(wheel, artifact.parent)
    assert artifact.read_bytes() == original


@pytest.mark.parametrize('tag', ['v9.9.9', '../escape', ''])
def test_release_tag_mismatch_does_not_create_output(wheel, tmp_path, tag):
    with pytest.raises(ValueError, match='tag'):
        bundle.build_bundle(wheel, tmp_path / 'output', tag=tag)
    assert not (tmp_path / 'output').exists()


@pytest.mark.parametrize('extra', ['docs/legacy.md', '.env', 'web/.env.local',
                                   'storage/library.sqlite3-wal', 'storage/library.sqlite3',
                                   'web/personal.pdf', '../outside', 'storage/../outside',
                                   'web/log/session.txt', 'storage/logs/trace.txt',
                                   'litradar_runtime/trace.log.1', 'web/TRACE.LOG.2'])
def test_unrelated_or_local_data_never_shipped(wheel, tmp_path, extra):
    with ZipFile(wheel, 'a') as archive:
        archive.writestr(extra, 'Synthetic only')
    with pytest.raises(ValueError):
        bundle.build_bundle(wheel, tmp_path / 'output')
    assert not (tmp_path / 'output').exists()


def test_version_disagreement_rejected(wheel, tmp_path):
    replacement = tmp_path / 'litradar-wrong-py3-none-any.whl'
    with ZipFile(wheel) as source, ZipFile(replacement, 'w') as target:
        for name in source.namelist():
            target.writestr(name, b'9.9.9' if name.endswith('/VERSION') else source.read(name))
    with pytest.raises(ValueError, match='version'):
        bundle.build_bundle(replacement, tmp_path / 'output')


def test_filename_version_disagreement_rejected(wheel, tmp_path):
    replacement = tmp_path / 'litradar-9.9.9-py3-none-any.whl'
    replacement.write_bytes(wheel.read_bytes())
    with pytest.raises(ValueError, match='filename'):
        bundle.build_bundle(replacement, tmp_path / 'output')


def test_corrupt_wheel_cli_reports_failure_without_output(tmp_path, capsys):
    wheel = tmp_path / f'litradar-{(bundle.ROOT / "VERSION").read_text().strip()}-py3-none-any.whl'
    wheel.write_bytes(b'not a wheel')
    with pytest.raises(SystemExit) as exc:
        bundle.main([str(wheel), '--output-dir', str(tmp_path / 'output')])
    assert exc.value.code == 1 and 'failed' in capsys.readouterr().err
    assert not (tmp_path / 'output').exists()


def test_duplicate_entries_rejected(wheel, tmp_path):
    with ZipFile(wheel, 'a') as archive:
        with pytest.warns(UserWarning, match='Duplicate'):
            archive.writestr('cli.py', 'duplicate')
    with pytest.raises(ValueError, match='duplicate'):
        bundle.build_bundle(wheel, tmp_path / 'output')


def test_failed_zip_write_removes_partial_artifact(wheel, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise OSError('Synthetic disk failure')
    monkeypatch.setattr(ZipFile, 'write', fail)
    with pytest.raises(OSError, match='disk failure'):
        bundle.build_bundle(wheel, tmp_path / 'output')
    assert list((tmp_path / 'output').iterdir()) == []
