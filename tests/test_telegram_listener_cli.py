"""CLI-level listener failures use only fake credentials and disposable paths."""
from __future__ import annotations

import io
import json
from pathlib import Path
import urllib.error

import pytest

import cli
import telegram_bot


@pytest.fixture(autouse=True)
def disposable_log_root(tmp_path, monkeypatch):
    import litradar_runtime
    monkeypatch.setattr(litradar_runtime, "LOG_ROOT", tmp_path / "log")


POISON = 'synthetic-private-note https://api.telegram.org/botfake-sensitive-token/getUpdates'


def listener_args(tmp_path: Path, *options: str):
    return cli.build_parser().parse_args([
        '--db', str(tmp_path / 'library.sqlite3'), 'telegram-run',
        '--config', str(tmp_path / 'config.json'), '--profile', str(tmp_path / 'profile.json'),
        *options,
    ])


def fake_credentials(monkeypatch):
    monkeypatch.setattr(cli.RadarConfig, 'load', lambda: None)
    monkeypatch.setenv('LITRADAR_TELEGRAM_BOT_TOKEN', 'fake-sensitive-token')
    monkeypatch.setenv('LITRADAR_TELEGRAM_CHAT_ID', '123456789')


def test_cli_polling_conflict_exits_without_sleep_or_offset_changes(tmp_path, monkeypatch, capsys):
    fake_credentials(monkeypatch)
    state = tmp_path / 'state.json'
    state.write_text('{"next_update_offset": 42}', encoding='utf-8')
    before = state.read_bytes()
    calls = []

    class Reply:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, *args): return b'{"ok":true,"result":true}'

    def urlopen(request, **kwargs):
        method = request.full_url.rsplit('/', 1)[-1]
        calls.append(method)
        if method == 'getUpdates':
            raise urllib.error.HTTPError(request.full_url, 409, POISON, {},
                                         io.BytesIO(json.dumps({'description': POISON}).encode()))
        return Reply()

    monkeypatch.setattr(telegram_bot.urllib.request, 'urlopen', urlopen)
    monkeypatch.setattr(telegram_bot.time, 'sleep', lambda *_: pytest.fail('Conflict must not retry'))
    real_bot = telegram_bot.LitRadarTelegramBot
    monkeypatch.setattr(cli, 'LitRadarTelegramBot', lambda **kwargs: real_bot(**kwargs, state_path=state))
    log = tmp_path / 'log' / 'listener.log'
    args = listener_args(tmp_path, '--debug', '--log-file', str(log))
    assert args.func(args) == 2
    assert calls == ['setMyCommands', 'getUpdates']
    assert state.read_bytes() == before
    assert not (tmp_path / 'library.sqlite3').exists()
    console = capsys.readouterr().err
    text = console + log.read_text(encoding='utf-8')
    assert '409' in text and 'webhook' in text.lower()
    assert 'poll' in text.lower()
    for private in (POISON, 'fake-sensitive-token', '123456789'):
        assert private not in text


@pytest.mark.parametrize('error', [ValueError(POISON), OSError(POISON), RuntimeError(POISON), KeyError(POISON), TypeError(POISON)])
def test_cli_local_startup_failure_omits_private_details(tmp_path, monkeypatch, capsys, error):
    fake_credentials(monkeypatch)
    def fail(**kwargs): raise error
    monkeypatch.setattr(cli, 'LitRadarTelegramBot', fail)
    log = tmp_path / 'log' / 'listener.log'
    args = listener_args(tmp_path, '--log-file', str(log))
    assert args.func(args) == 2
    text = capsys.readouterr().err + log.read_text(encoding='utf-8')
    assert 'configuration' in text.lower()
    assert POISON not in text and 'fake-sensitive-token' not in text


def test_cli_missing_credentials_is_actionable_without_starting_bot(tmp_path, monkeypatch, capsys):
    fake_credentials(monkeypatch)
    monkeypatch.delenv('LITRADAR_TELEGRAM_BOT_TOKEN')
    monkeypatch.setattr(cli, 'LitRadarTelegramBot', lambda **_: pytest.fail('Bot must not start'))
    args = listener_args(tmp_path)
    assert args.func(args) == 2
    text = capsys.readouterr().err
    assert 'LITRADAR_TELEGRAM_BOT_TOKEN' in text
    assert '123456789' not in text
    assert list(tmp_path.iterdir()) == []


def test_cli_unwritable_log_fails_before_loading_credentials(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli.RadarConfig, 'load', lambda: pytest.fail('No credentials for failed log setup'))
    args = listener_args(tmp_path, '--log-file', str(tmp_path))
    assert args.func(args) == 2
    assert 'writable log filename' in capsys.readouterr().err


def test_cli_user_stop_returns_success_and_does_not_log_private_text(tmp_path, monkeypatch, capsys):
    fake_credentials(monkeypatch)
    class Stopped:
        def __init__(self, **kwargs): pass
        def run_forever(self, **kwargs): raise KeyboardInterrupt(POISON)
    monkeypatch.setattr(cli, 'LitRadarTelegramBot', Stopped)
    args = listener_args(tmp_path)
    assert args.func(args) == 0
    assert POISON not in capsys.readouterr().err
