from __future__ import annotations

import argparse
import json
from pathlib import Path

from cli import _write_job_enablement, cmd_scheduled_run
from telegram_bot import LitRadarTelegramBot


def _config(path: Path):
    path.write_text(json.dumps({
        "queries": [], "scan": {"semantic": False, "enabled": True},
        "digest": {"limit": 10}, "delivery": {"frequency": "weekly", "time": "09:00", "enabled": True}
    }), encoding="utf-8")
    return path


def test_cli_can_disable_one_job_without_disabling_the_other(tmp_path):
    config = _config(tmp_path / "digest_config.json")
    _write_job_enablement(config, "remove", "digest")
    data = json.loads(config.read_text(encoding="utf-8"))
    assert data["delivery"]["enabled"] is False
    assert data["scan"]["enabled"] is True
    _write_job_enablement(config, "install", "scan", frequency="daily", when="07:30")
    data = json.loads(config.read_text(encoding="utf-8"))
    assert data["scan"]["enabled"] is True
    assert data["delivery"]["enabled"] is False


def test_disabled_scheduled_run_exits_without_running_network_jobs(tmp_path, capsys):
    config = _config(tmp_path / "digest_config.json")
    _write_job_enablement(config, "remove", "scan")
    args = argparse.Namespace(job="scan", config=str(config))
    assert cmd_scheduled_run(args) == 0
    assert "is disabled" in capsys.readouterr().out


def test_telegram_bot_removes_only_requested_scheduled_job(tmp_path):
    config = _config(tmp_path / "digest_config.json")
    calls = []
    sent = []
    def api(token, method, payload=None, *, timeout=35):
        if method == "sendMessage":
            sent.append(payload.get("text", ""))
        return {"ok": True, "result": []}
    bot = LitRadarTelegramBot(
        token="fake", chat_id="123", config_path=config, db_path=tmp_path / "db.sqlite3",
        profile_path=tmp_path / "profile.json", state_path=tmp_path / "state.json", api=api,
        schedule_remover=lambda job: (calls.append(job) is None, f"removed {job}"),
    )
    bot.process_update({"update_id": 1, "message": {"chat": {"id": 123}, "text": "/schedule remove digest"}})
    data = json.loads(config.read_text(encoding="utf-8"))
    assert calls == ["digest"]
    assert data["delivery"]["enabled"] is False
    assert data["scan"]["enabled"] is True
    assert any("Завдання вимкнено: digest" in message for message in sent)


def test_schedule_help_explains_per_job_removal():
    from cli import build_parser
    assert "remove" in build_parser().format_help().lower()
