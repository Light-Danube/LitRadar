"""Application diagnostics stay in disposable log roots; no credentials/services."""
import logging
import shutil
from logging.handlers import RotatingFileHandler
from pathlib import Path
import stat
import subprocess
from types import SimpleNamespace

import pytest

import litradar_runtime as runtime
import telegram_bot


@pytest.fixture
def log_root(tmp_path, monkeypatch):
    root = tmp_path / "workspace" / "log"
    monkeypatch.setattr(runtime, "LOG_ROOT", root)
    return root


def test_log_root_uses_workspace_and_resolution_does_not_create_files(log_root):
    assert runtime.resolve_log_path("listener.log") == log_root / "listener.log"
    assert runtime.resolve_log_path("log/listener.log") == log_root / "listener.log"
    assert runtime.resolve_log_path(log_root / "listener.log") == log_root / "listener.log"
    assert not log_root.exists()


def test_console_only_does_not_create_log_directory(log_root):
    with telegram_bot.configure_listener_logging() as logger:
        logger.info("Synthetic console only")
    assert not log_root.exists()


@pytest.mark.parametrize("value", ["", ".", "log", "../outside.log", "log/../outside.log", "log/./listener.log", "log\\..\\outside.log", "C:outside.log", "name:stream"])
def test_invalid_log_paths_leave_workspace_uncreated(log_root, value):
    with pytest.raises(ValueError):
        runtime.resolve_log_path(value)
    assert not log_root.parent.exists()


def test_outside_absolute_path_rejected_before_touching_file(log_root, tmp_path):
    outside = tmp_path / "outside.log"
    outside.write_text("Synthetic keep", encoding="utf-8")
    logger = telegram_bot.LOGGER
    previous = (logger.handlers[:], logger.level, logger.propagate, logger.disabled)
    with pytest.raises(ValueError):
        with telegram_bot.configure_listener_logging(log_file=outside):
            pytest.fail("Outside path must fail before logging")
    assert (logger.handlers, logger.level, logger.propagate, logger.disabled) == previous
    assert outside.read_text(encoding="utf-8") == "Synthetic keep"
    assert not log_root.exists()


def test_explicit_filename_creates_rotating_log_and_restores_logger(log_root):
    logger = logging.getLogger("litradar.telegram")
    previous = (logger.handlers[:], logger.level, logger.propagate, logger.disabled)
    with pytest.raises(RuntimeError, match="Synthetic stop"):
        with telegram_bot.configure_listener_logging(debug=True, log_file="listener.log"):
            handler = next(handler for handler in logger.handlers if isinstance(handler, RotatingFileHandler))
            assert Path(handler.baseFilename) == log_root / "listener.log"
            assert handler.maxBytes == 1024 * 1024 and handler.backupCount == 3
            handler.maxBytes = 100
            for index in range(6):
                logger.info("Synthetic rotation marker %s", index)
            raise RuntimeError("Synthetic stop")
    assert (logger.handlers, logger.level, logger.propagate, logger.disabled) == previous
    assert (log_root / "listener.log.1").is_file()
    for path in log_root.iterdir():
        assert "Synthetic rotation marker" in path.read_text(encoding="utf-8")
        path.unlink()  # Requires every file handle closed on Windows too.


@pytest.mark.parametrize("link_location", ["root", "parent", "file", "rotation"])
def test_symlink_log_escape_is_rejected(log_root, tmp_path, link_location):
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "keep.log"
    marker.write_text("Synthetic keep", encoding="utf-8")
    log_root.parent.mkdir(parents=True)
    try:
        if link_location == "root":
            log_root.symlink_to(outside, target_is_directory=True)
            selected = "keep.log"
        else:
            log_root.mkdir()
            if link_location == "parent":
                (log_root / "linked").symlink_to(outside, target_is_directory=True)
                selected = "linked/keep.log"
            else:
                (log_root / ("listener.log.1" if link_location == "rotation" else "listener.log")).symlink_to(marker)
                selected = "listener.log"
    except OSError as exc:
        pytest.skip(f"Platform does not permit creating synthetic symlinks: {exc}")
    with pytest.raises(ValueError, match="Linked"):
        with telegram_bot.configure_listener_logging(log_file=selected):
            pytest.fail("Linked path must fail before logging")
    assert marker.read_text(encoding="utf-8") == "Synthetic keep"


def test_windows_reparse_log_root_rejected(log_root, monkeypatch):
    real_lstat = Path.lstat
    def reparse(path, *args, **kwargs):
        if path == log_root:
            return SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0x400)
        return real_lstat(path, *args, **kwargs)
    monkeypatch.setattr(Path, "lstat", reparse)
    with pytest.raises(ValueError, match="Linked"):
        runtime.resolve_log_path("listener.log")
    assert not log_root.exists()


def test_git_and_docker_ignore_logs_and_rotations(tmp_path):
    root = Path(__file__).resolve().parents[1]
    git_patterns = (root / ".gitignore").read_text(encoding="utf-8")
    docker_patterns = (root / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert {"log/", "*.log", "*.log.*"} <= set(git_patterns.splitlines())
    assert {"log/", "*.log", "*.log.*"} <= set(docker_patterns)
    # The minimal Docker profile has no Git; still verify both contract files above.
    if shutil.which("git") is None:
        return
    (tmp_path / ".gitignore").write_text(git_patterns, encoding="utf-8")
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True, capture_output=True)
    filenames = ["log/listener.log", "log/listener.log.1", "log/diagnostics.txt", "legacy-listener.log", "legacy-listener.log.1"]
    for filename in filenames:
        path = tmp_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("Synthetic diagnostics", encoding="utf-8")
    ignored = subprocess.run(["git", "check-ignore", "--no-index", *filenames], cwd=tmp_path,
                             check=True, capture_output=True, text=True)
    assert set(ignored.stdout.splitlines()) == set(filenames)
