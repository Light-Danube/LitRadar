"""Isolated real-I/O shutdown probes; no live Telegram or host data is used."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest


# A child keeps real signals away from pytest's console. Its HTTP adapter rewrites
# every Telegram request to a disposable loopback server before any I/O occurs.
PROBE = r'''
import _thread
from contextlib import closing
import ctypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys
import threading
import time
import urllib.request

root, stage, interrupt_mode = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3]
backoff_stage = stage in {"backoff", "rate_backoff"}
exit_with_pending = stage == "exit_poll"
os.environ["LITBEACON_HOME"] = str(root / "home")
baseline = os.environ.get("LITBEACON_SHUTDOWN_BASELINE")
if baseline:
    spec = importlib.util.spec_from_file_location("telegram_shutdown_baseline", baseline)
    telegram = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(telegram)
else:
    import telegram_bot as telegram
from sources.base import Paper

entered, release, transport_finished = threading.Event(), threading.Event(), threading.Event()
interrupt_sent = []
controller_errors = []
processed = []
calls = []
state = root / "state.json"
config = root / "config.json"
profile = root / "profile.json"
database = root / "synthetic.sqlite3"
state.write_text('{"next_update_offset":41}', encoding="utf-8")
config.write_text('{"digest":{"limit":15}}', encoding="utf-8")
profile.write_text('{"groups":[]}', encoding="utf-8")
store = telegram.PaperStore(database)
paper_id = store.upsert_paper(Paper(source="fixture", title="Synthetic shutdown paper"),
                             relevance_score=0, matched_groups={})
store.set_notes(paper_id, "Synthetic saved manual note")
store.close()
sources = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in (state, config, profile, database)}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        method = self.path.rsplit("/", 1)[-1]
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        result = [{"update_id":41,"message":{"chat":{"id":12345},"text":"/limit 9"}}] if method == "getUpdates" else True
        data = json.dumps({"ok":True,"result":result}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.flush()
        if method == ("setMyCommands" if stage == "menu" else "getUpdates"):
            entered.set()
            release.wait(10 if exit_with_pending else 3.5)
        try:
            self.wfile.write(data)
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
server.daemon_threads = True
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()
original_urlopen = urllib.request.urlopen

def loopback_urlopen(request, timeout=35, **kwargs):
    method = request.full_url.rsplit("/", 1)[-1]
    calls.append(method)
    local = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/{method}",
                                   data=request.data, headers={"Content-Type":"application/json"}, method="POST")
    return original_urlopen(local, timeout=timeout)

telegram.urllib.request.urlopen = loopback_urlopen
def api(token, method, payload=None, **kwargs):
    try:
        if backoff_stage:
            calls.append(method)
            if method == "getUpdates":
                entered.set()
                raise telegram.TelegramAPIError(status_code=429 if stage == "rate_backoff" else 503,
                                                retry_after=19 if stage == "rate_backoff" else 5,
                                                retryable=True)
            return {"ok":True,"result":True}
        return telegram.telegram_api(token, method, payload, **kwargs)
    finally:
        if method == ("setMyCommands" if stage == "menu" else "getUpdates") and not backoff_stage:
            transport_finished.set()

bot = telegram.LitRadarTelegramBot(token="synthetic-unused-token", chat_id="12345", api=api,
    state_path=state, config_path=config, profile_path=profile, db_path=database)
original_process = bot.process_update
def process(update):
    processed.append(update)
    original_process(update)
bot.process_update = process

def interrupt():
    if not entered.wait(5):
        controller_errors.append("blocked operation was never entered")
    time.sleep(.15)
    interrupt_sent.append(time.monotonic())
    if interrupt_mode == "posix":
        os.kill(os.getpid(), signal.SIGINT)
    elif interrupt_mode == "windows_console":
        kernel = ctypes.windll.kernel32
        if not kernel.GetConsoleCP() or not kernel.GenerateConsoleCtrlEvent(0, 0):
            controller_errors.append("isolated Windows console Ctrl+C generation failed")
            _thread.interrupt_main()
    else:
        _thread.interrupt_main()

controller = threading.Thread(target=interrupt, daemon=True)
controller.start()
handlers = []
with telegram.configure_listener_logging(debug=True, log_file="shutdown.log"):
    handlers = list(telegram.LOGGER.handlers)
    bot.run_forever(timeout=25)
    stopped = time.monotonic()
log_file = root / "home" / "log" / "shutdown.log"
log_at_stop = log_file.read_bytes()
if exit_with_pending:
    assert not transport_finished.is_set(), "exit probe needs an outstanding HTTP request"
else:
    release.set()
    if not backoff_stage:
        assert transport_finished.wait(2), "abandoned local transport did not complete after release"
time.sleep(.15)  # Give the returned response a chance to cause an incorrect late write.
assert not controller_errors, controller_errors
assert interrupt_sent, "no main-thread interrupt was requested"
assert not processed, "updates returned after stop must never be dispatched"
assert bot.offset == 41, "abandoned updates must not advance the polling offset"
assert {p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in (state,config,profile,database)} == sources
assert log_file.read_bytes() == log_at_stop, "abandoned transport must not log after context closure"
assert all(getattr(handler, "stream", None) is None for handler in handlers if hasattr(handler,"baseFilename"))
assert b"stopped" in log_at_stop.lower()
if stage == "menu":
    assert "getUpdates" not in calls, "cancelled menu setup must not start a poll"
else:
    assert calls.count("getUpdates") == 1, "shutdown must not launch another poll"
server.shutdown()
server.server_close()
print(json.dumps({"latency":stopped-interrupt_sent[0],"interrupted_at":interrupt_sent[0],"stage":stage,"interrupt":interrupt_mode,
                  "processed":len(processed),"offset":bot.offset}), flush=True)
'''


def run_probe(tmp_path, stage, interrupt_mode="pending", *, baseline=None):
    environment = os.environ.copy()
    root = str(Path(__file__).resolve().parents[1])
    environment["PYTHONPATH"] = os.pathsep.join(filter(None, [root, environment.get("PYTHONPATH")]))
    environment.pop("LITBEACON_SHUTDOWN_BASELINE", None)
    if baseline is not None:
        environment["LITBEACON_SHUTDOWN_BASELINE"] = str(baseline)
    result = subprocess.run([sys.executable, "-c", PROBE, str(tmp_path), stage, interrupt_mode],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=5 if stage == "rate_backoff" else 15,
        creationflags=subprocess.CREATE_NEW_CONSOLE if interrupt_mode == "windows_console" else 0)
    assert result.returncode == 0, result.stdout + result.stderr
    values = json.loads(result.stdout.strip().splitlines()[-1])
    values["exit_latency"] = time.monotonic() - values["interrupted_at"]
    return values


@pytest.mark.parametrize("stage", ["poll", "menu", "backoff", "rate_backoff"])
def test_pending_main_thread_interrupt_stops_real_blocked_io_promptly(tmp_path, stage):
    result = run_probe(tmp_path, stage)
    assert result["latency"] < 2.0, result


@pytest.mark.parametrize("mode", ["windows_console"] if os.name == "nt" else ["posix"])
def test_native_interrupt_isolated_from_pytest_console_stops_blocked_poll(tmp_path, mode):
    result = run_probe(tmp_path, "poll", mode)
    assert result["latency"] < 2.0, result


def test_process_exits_without_joining_abandoned_http_request(tmp_path):
    result = run_probe(tmp_path, "exit_poll")
    assert result["latency"] < 2.0 and result["exit_latency"] < 2.0, result


def test_background_transport_preserves_fatal_exception_identity(tmp_path):
    import telegram_bot as telegram

    error = telegram.TelegramAPIError(status_code=401, retryable=False)
    calls = []
    def api(token, method, payload=None, **kwargs):
        calls.append(method)
        if method == "getUpdates":
            raise error
        return {"ok":True,"result":True}
    bot = telegram.LitRadarTelegramBot(token="synthetic-unused-token", chat_id="12345", api=api,
        state_path=tmp_path / "state.json", config_path=tmp_path / "config.json",
        profile_path=tmp_path / "profile.json", db_path=tmp_path / "synthetic.sqlite3")
    with pytest.raises(telegram.TelegramAPIError) as raised:
        bot.run_forever()
    assert raised.value is error
    assert calls == ["setMyCommands", "getUpdates"]
    assert not list(tmp_path.iterdir())


def test_updates_and_offsets_remain_on_main_thread(tmp_path):
    import telegram_bot as telegram

    polls, processed_threads = [], []
    def api(token, method, payload=None, **kwargs):
        if method == "getUpdates":
            polls.append(payload)
            if len(polls) == 1:
                return {"ok":True,"result":[{"update_id":42}]}
            raise KeyboardInterrupt
        return {"ok":True,"result":True}
    state = tmp_path / "state.json"
    bot = telegram.LitRadarTelegramBot(token="synthetic-unused-token", chat_id="12345", api=api,
        state_path=state, config_path=tmp_path / "config.json",
        profile_path=tmp_path / "profile.json", db_path=tmp_path / "synthetic.sqlite3")
    bot.process_update = lambda update: processed_threads.append(threading.get_ident())
    assert bot.run_forever() is None
    assert processed_threads == [threading.main_thread().ident]
    assert json.loads(state.read_text(encoding="utf-8"))["next_update_offset"] == 43
    assert polls[1]["offset"] == 43
