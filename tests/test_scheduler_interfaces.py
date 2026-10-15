"""Scheduler subprocesses retain selected libraries; no OS scheduler is contacted."""
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest


def _paths(tmp_path):
    return (tmp_path / "selected library.sqlite3", tmp_path / "selected profile.json",
            tmp_path / "selected digest.json")


@pytest.mark.parametrize("action,job", [
    ("status", "all"), ("install", "scan"), ("install", "digest"),
    ("remove", "scan"), ("remove", "digest"), ("remove", "all"),
])
def test_tui_scheduler_retains_selected_paths(tmp_path, monkeypatch, action, job):
    pytest.importorskip("textual", reason="Textual UI dependency is optional")
    import ui

    db, profile, config = _paths(tmp_path)
    calls = []
    monkeypatch.setattr(ui, "get_current_worker", lambda: SimpleNamespace(is_cancelled=False))
    monkeypatch.setattr(ui.subprocess, "run", lambda command, **kw:
                        calls.append((command, kw)) or subprocess.CompletedProcess(command, 0, "ok", ""))
    screen = SimpleNamespace(db_path=db, profile_path=profile, config_path=config,
                             app=SimpleNamespace(is_running=False))
    ui.ScheduleScreen._run_schedule.__wrapped__(screen, action, job, "weekly", "09:15")
    assert calls == [([
        sys.executable, str(Path(ui.__file__).resolve().parent / "cli.py"),
        "--db", str(db.resolve()), "schedule", action, "--job", job,
        "--frequency", "weekly", "--time", "09:15", "--config", str(config.resolve()),
        "--profile", str(profile.resolve()),
    ], dict(cwd=ui.WORKSPACE_ROOT, capture_output=True, text=True, timeout=60, check=False))]
    assert not db.exists()
    assert not profile.exists()
    assert not config.exists()


def test_tui_jobs_dialog_keeps_current_app_library_and_legacy_constructor(tmp_path, monkeypatch):
    pytest.importorskip("textual", reason="Textual UI dependency is optional")
    import ui

    monkeypatch.setattr(ui, "ensure_user_defaults", lambda: None)
    db, profile, config = _paths(tmp_path)
    legacy = ui.ScheduleScreen(config, "uk")
    assert legacy.config_path == config
    assert legacy.language == "uk"
    assert legacy.db_path == ui.DEFAULT_DB
    assert legacy.profile_path == ui.DEFAULT_PROFILE
    explicit = ui.ScheduleScreen(config, "uk", db_path=db, profile_path=profile)
    assert explicit.db_path == db
    assert explicit.profile_path == profile
    screens = []
    app = SimpleNamespace(db_path=str(db), language="uk", push_screen=screens.append)
    ui.LitRadarApp.action_manage_jobs(app)
    assert len(screens) == 1
    assert screens[0].db_path == db
    assert screens[0].language == "uk"
    assert not db.exists()


@pytest.mark.parametrize("action,job", [("install", "digest"), ("remove", "scan"),
                                      ("remove", "digest"), ("remove", "all")])
def test_telegram_scheduler_retains_selected_paths(tmp_path, monkeypatch, action, job):
    import telegram_bot

    db, profile, config = _paths(tmp_path)
    calls = []
    monkeypatch.setattr(telegram_bot, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(telegram_bot.subprocess, "run", lambda command, **kw:
                        calls.append(command) or subprocess.CompletedProcess(command, 0, "ok", ""))
    bot = telegram_bot.LitRadarTelegramBot(token="synthetic-token", chat_id="synthetic-chat",
        db_path=db, profile_path=profile, config_path=config, state_path=tmp_path / "state.json",
        api=lambda *args, **kwargs: pytest.fail("No Telegram request is expected"))
    expected = [sys.executable, str(telegram_bot.CODE_ROOT / "cli.py"),
                "--db", str(db.resolve()), "schedule", action, "--job", job]
    if action == "install":
        ok, _ = bot._reschedule("weekly", "09:15")
        expected += ["--frequency", "weekly", "--time", "09:15"]
    else:
        ok, _ = bot._remove_scheduled_jobs(job)
    expected += ["--config", str(config.resolve()), "--profile", str(profile.resolve())]
    assert ok
    assert calls == [expected]
    assert not db.exists()
    assert not config.exists()
    assert not profile.exists()
