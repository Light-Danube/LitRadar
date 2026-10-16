"""Local launch contract, including a real socket; no personal data or providers."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
import urllib.error
import urllib.request

import pytest

import cli


@pytest.fixture
def launch_calls(monkeypatch):
    calls = []
    app = object()
    monkeypatch.setitem(sys.modules, "workspace_web", SimpleNamespace(
        create_app=lambda db: calls.append(("app", db)) or app,
    ))
    monkeypatch.setitem(sys.modules, "uvicorn", SimpleNamespace(
        run=lambda selected, **kwargs: calls.append(("server", selected, kwargs)),
    ))
    monkeypatch.setattr(cli.webbrowser, "open", lambda url: calls.append(("browser", url)))
    return calls, app


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "::1", "192.0.2.10", "example.invalid"])
def test_external_bind_rejected_by_parser_and_command(host, launch_calls, tmp_path, capsys):
    calls, _ = launch_calls
    with pytest.raises(SystemExit) as rejected:
        cli.build_parser().parse_args(["web", "--host", host])
    assert rejected.value.code == 2
    db = tmp_path / "not-created" / "library.sqlite3"
    # Exercise the command guard independently of argparse's choices.
    args = argparse.Namespace(host=host, port=8765, db=str(db), open_browser=True)
    assert cli.cmd_web(args) == 2
    assert "only binds to localhost" in capsys.readouterr().err
    assert calls == []
    assert not db.parent.exists()


@pytest.mark.parametrize("host,open_browser", [(None, False), ("127.0.0.1", True), ("localhost", False)])
def test_loopback_launch_preserves_host_port_database_and_browser_choice(
    host, open_browser, launch_calls, monkeypatch, tmp_path, capsys,
):
    calls, app = launch_calls
    monkeypatch.setenv("UVICORN_HOST", "0.0.0.0")
    db = str(tmp_path / "chosen.sqlite3")
    argv = ["--db", db, "web", "--port", "8787"]
    if host is not None:
        argv += ["--host", host]
    argv += ["--open-browser" if open_browser else "--no-open-browser"]
    args = cli.build_parser().parse_args(argv)
    assert args.host == (host or "127.0.0.1")
    assert args.func(args) == 0
    expected = [("browser", "http://127.0.0.1:8787")] if open_browser else []
    expected += [("app", db), ("server", app, {
        "host": host or "127.0.0.1", "port": 8787, "log_level": "info",
    })]
    assert calls == expected
    assert "http://127.0.0.1:8787 (local-only)" in capsys.readouterr().out


# Observe actual listening sockets after startup, including optional uvloop;
# do not replace the bind or choose the host/port for the CLI.
SOCKET_PROBE = r'''
import importlib
import json
from pathlib import Path
import runpy
import sys
import uvicorn

probe_root = Path(sys.argv[1])
class ObservedServer(uvicorn.Server):
    async def startup(self, sockets=None):
        await super().startup(sockets=sockets)
        addresses = [sock.getsockname() for server in self.servers for sock in server.sockets]
        temporary = probe_root / "binds.tmp"
        temporary.write_text(json.dumps(addresses), encoding="utf-8")
        temporary.replace(probe_root / "binds.json")
importlib.import_module("uvicorn.main").Server = ObservedServer
sys.argv = ["cli", "--db", str(probe_root / "library.sqlite3"), "web",
            "--port", "0", "--no-open-browser"]
runpy.run_module("cli", run_name="__main__")
'''


def test_real_cli_listener_binds_only_ipv4_loopback(tmp_path):
    pytest.importorskip("uvicorn", reason="real web listener requires optional web dependencies")
    pytest.importorskip("fastapi", reason="real web listener requires optional web dependencies")
    environment = os.environ.copy()
    environment["LITBEACON_HOME"] = str(tmp_path / "home")
    environment["UVICORN_HOST"] = "0.0.0.0"
    # Bypass inherited HTTP proxies only for this disposable loopback request.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with (tmp_path / "server-output.txt").open("w+", encoding="utf-8") as output:
        process = subprocess.Popen(
            [sys.executable, "-c", SOCKET_PROBE, str(tmp_path)],
            cwd=Path(__file__).resolve().parents[1], env=environment,
            stdout=output, stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 20
            health = None
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    output.seek(0)
                    pytest.fail("Disposable web listener exited: " + output.read())
                record = tmp_path / "binds.json"
                if record.exists():
                    addresses = json.loads(record.read_text(encoding="utf-8"))
                    assert addresses and all(address[0] == "127.0.0.1" for address in addresses)
                    try:
                        with opener.open(f"http://127.0.0.1:{addresses[0][1]}/api/health", timeout=1) as response:
                            health = json.load(response)
                        break
                    except (urllib.error.URLError, TimeoutError):
                        pass
                time.sleep(0.05)
            assert health is not None, "Disposable loopback server did not become ready"
            assert health["ok"] is True
            assert health["legacy_name"] == "LitRadar"
            with opener.open(f"http://127.0.0.1:{addresses[0][1]}/api/summary", timeout=5) as response:
                summary = json.load(response)
            assert summary["stats"]["all"] == 0
            assert (tmp_path / "library.sqlite3").is_file()
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
