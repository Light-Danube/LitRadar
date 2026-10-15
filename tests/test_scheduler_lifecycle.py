"""Synthetic scheduler lifecycle; Windows OS calls are replaced, never personal tasks."""
import argparse
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

import cli
import litradar_runtime


@pytest.fixture
def configuration(tmp_path):
    path = tmp_path / "custom settings.json"
    path.write_text(json.dumps({"queries": ["synthetic"], "scan": {"enabled": True, "semantic": False},
                                "delivery": {"enabled": True, "time": "09:00"}, "digest": {"limit": 3}}), encoding="utf-8")
    return path


def arguments(configuration, action="remove", job="all"):
    return argparse.Namespace(config=str(configuration), action=action, job=job, frequency="daily", time="08:00",
                              db=str(configuration.parent / "custom database.sqlite3"),
                              profile=str(configuration.parent / "custom profile.json"), period="daily")


def windows(monkeypatch):
    # Replacing only cli.os avoids changing pathlib's platform on a Linux runner.
    monkeypatch.setattr(cli, "os", SimpleNamespace(name="nt", replace=os.replace, chmod=os.chmod,
                                                   fsync=os.fsync, getenv=os.getenv))
    monkeypatch.setattr(cli, "SOURCE_CHECKOUT", True)


@pytest.mark.parametrize("job", ["scan", "digest", "all"])
def test_remove_disables_selected_jobs_even_if_os_removal_fails(configuration, monkeypatch, capsys, job):
    windows(monkeypatch)
    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1))
    args = arguments(configuration, job=job)
    assert cli.cmd_schedule(args) == 1
    payload = json.loads(configuration.read_text())
    assert payload["scan"]["enabled"] is (job == "digest")
    assert payload["delivery"]["enabled"] is (job == "scan")
    assert payload["digest"] == {"limit": 3} and payload["queries"] == ["synthetic"]
    assert "remains disabled" in capsys.readouterr().err
    monkeypatch.setattr(cli, "cmd_scan", lambda _: pytest.fail("Disabled scan must not run"))
    monkeypatch.setattr(cli, "cmd_digest", lambda _: pytest.fail("Disabled digest must not run"))
    for selected in (("scan", "digest") if job == "all" else (job,)):
        args.job = selected
        assert cli.cmd_scheduled_run(args) == 0


@pytest.mark.parametrize("broken", ["not json", "[]", '{"scan": []}', '{"scan": null}'])
def test_bad_config_is_unchanged_and_prevents_os_install_or_remove(configuration, monkeypatch, broken):
    configuration.write_text(broken)
    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: pytest.fail("Invalid config must not call OS helper"))
    for action in ("install", "remove"):
        assert cli.cmd_schedule(arguments(configuration, action=action)) == 2
        assert configuration.read_text() == broken
    assert not list(configuration.parent.glob(".*.tmp"))


def test_atomic_write_failure_does_not_claim_disabled_or_touch_os(configuration, monkeypatch, capsys):
    before = configuration.read_bytes()
    windows(monkeypatch)
    def fail(*args): raise PermissionError("Synthetic private text")
    monkeypatch.setattr(cli.os, "replace", fail)
    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: pytest.fail("Failed persistence must precede OS removal"))
    assert cli.cmd_schedule(arguments(configuration)) == 2
    assert configuration.read_bytes() == before
    assert not list(configuration.parent.glob(".*.tmp"))
    output = capsys.readouterr()
    assert "not updated" in output.err and "private text" not in output.err


def test_enablement_atomic_replace_retains_mode_and_unrelated_data(configuration):
    os.chmod(configuration, 0o600)
    before_mode = stat.S_IMODE(configuration.stat().st_mode)
    cli._write_job_enablement(configuration, "install", "digest", frequency="weekly", when="10:30")
    payload = json.loads(configuration.read_text())
    assert payload["scan"] == {"enabled": True, "semantic": False}
    assert payload["delivery"] == {"enabled": True, "time": "10:30", "frequency": "weekly"}
    assert stat.S_IMODE(configuration.stat().st_mode) == before_mode


def test_successful_install_forwards_selected_paths_and_enables_only_selected_job(configuration, monkeypatch):
    windows(monkeypatch)
    cli._write_job_enablement(configuration, "remove", "all")
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        assert json.loads(configuration.read_text())["scan"]["enabled"] is False
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(cli.subprocess, "run", run)
    args = arguments(configuration, action="install", job="scan")
    assert cli.cmd_schedule(args) == 0
    command = calls[0]
    for option, expected in (("-ConfigPath", args.config), ("-DatabasePath", args.db), ("-ProfilePath", args.profile)):
        assert command[command.index(option) + 1] == str(Path(expected).resolve())
    assert command[command.index("-PythonPath") + 1] == cli.sys.executable
    payload = json.loads(configuration.read_text())
    assert payload["scan"]["enabled"] is True and payload["delivery"]["enabled"] is False


def test_failed_install_does_not_enable_disabled_configuration(configuration, monkeypatch):
    windows(monkeypatch)
    cli._write_job_enablement(configuration, "remove", "all")
    before = configuration.read_bytes()
    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1))
    assert cli.cmd_schedule(arguments(configuration, action="install")) == 1
    assert configuration.read_bytes() == before


@pytest.mark.parametrize("contents", [None, "broken", "[]", '{"scan": null}', '{"scan": {"enabled": "false"}}'])
def test_invalid_scheduled_configuration_fails_closed_without_logs_or_network(configuration, monkeypatch, contents):
    if contents is None: configuration.unlink()
    else: configuration.write_text(contents)
    log_root = configuration.parent / "log"
    monkeypatch.setattr(litradar_runtime, "LOG_ROOT", log_root)
    monkeypatch.setattr(cli, "cmd_scan", lambda _: pytest.fail("No network job for invalid configuration"))
    assert cli.cmd_scheduled_run(arguments(configuration, job="scan")) == 2
    assert not log_root.exists()


def test_scheduled_run_uses_shared_log_folder_and_preserves_legacy_logs(configuration, monkeypatch):
    log_root = configuration.parent / "log"
    legacy = configuration.parent / "logs"
    legacy.mkdir()
    (legacy / "scheduled-scan.log").write_text("Synthetic legacy record")
    monkeypatch.setattr(litradar_runtime, "LOG_ROOT", log_root)
    monkeypatch.setattr(cli, "ROOT", configuration.parent)
    monkeypatch.setattr(cli, "cmd_scan", lambda _: 0)
    assert cli.cmd_scheduled_run(arguments(configuration, job="scan")) == 0
    assert "Job exit code: 0" in (log_root / "scheduled-scan.log").read_text()
    assert (legacy / "scheduled-scan.log").read_text() == "Synthetic legacy record"
    (log_root / "scheduled-scan.log").unlink()  # Windows handle closure.


def test_scheduler_logging_failure_prevents_job_execution(configuration, monkeypatch):
    log_root = configuration.parent / "log"
    log_root.write_text("Synthetic occupied log root")
    monkeypatch.setattr(litradar_runtime, "LOG_ROOT", log_root)
    monkeypatch.setattr(cli, "cmd_scan", lambda _: pytest.fail("No network job when diagnostics cannot open"))
    assert cli.cmd_scheduled_run(arguments(configuration, job="scan")) == 2
