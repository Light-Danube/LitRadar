"""Synthetic Telegram diagnostics: fake transport, disposable paths, no credentials."""
from __future__ import annotations

from contextlib import contextmanager
import io
import json
import logging
from logging.handlers import RotatingFileHandler
import re
from types import SimpleNamespace
import urllib.error

import pytest

import telegram_bot as telegram


TOKEN = "synthetic-token-never-real"
POISON = "REMOTE_PRIVATE_CONTENT_DO_NOT_LOG"
URL = f"https://api.telegram.org/bot{TOKEN}/getUpdates"


@contextmanager
def response(payload):
    yield io.BytesIO(payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8"))


def http_failure(monkeypatch, status, *, parameters=None, method="getUpdates"):
    body = {"ok": False, "error_code": status, "description": f"{POISON} {URL}"}
    if parameters is not None:
        body["parameters"] = parameters

    def fail(*args, **kwargs):
        raise urllib.error.HTTPError(URL, status, f"{POISON} {TOKEN}", {},
                                     io.BytesIO(json.dumps(body).encode("utf-8")))

    monkeypatch.setattr(telegram.urllib.request, "urlopen", fail)
    with pytest.raises(telegram.TelegramAPIError) as raised:
        telegram.telegram_api(TOKEN, method, {"private": POISON})
    return raised.value


def assert_private_content_absent(text):
    assert POISON not in text
    assert TOKEN not in text
    assert "api.telegram.org/bot" not in text


@pytest.mark.parametrize("status,retryable", [(400, False), (401, False), (403, False),
                                               (404, False), (409, False), (429, True),
                                               (500, True), (503, True)])
def test_http_errors_are_typed_actionable_and_do_not_echo_remote_content(monkeypatch, status, retryable):
    error = http_failure(monkeypatch, status)
    assert isinstance(error, RuntimeError)
    assert error.status_code == status
    assert error.retryable is retryable
    assert len(str(error)) > 20
    assert str(status) in str(error)
    assert_private_content_absent(str(error))
    assert isinstance(error, telegram.TelegramPollingConflict) is (status == 409)


def test_conflict_of_another_method_is_not_reported_as_duplicate_listener(monkeypatch):
    error = http_failure(monkeypatch, 409, method="sendMessage")
    assert not isinstance(error, telegram.TelegramPollingConflict)
    assert "polling" not in str(error).casefold()
    assert "webhook" not in str(error).casefold()
    assert "listener" not in str(error).casefold()


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 429, 503])
def test_json_rejections_have_the_same_failure_classification_as_http(monkeypatch, status):
    monkeypatch.setattr(telegram.urllib.request, "urlopen", lambda *a, **k: response({
        "ok": False, "error_code": status, "description": f"{POISON} {URL}"}))
    with pytest.raises(telegram.TelegramAPIError) as raised:
        telegram.telegram_api(TOKEN, "getUpdates")
    assert raised.value.status_code == status
    assert raised.value.retryable is (status == 429 or status >= 500)
    assert_private_content_absent(str(raised.value))
    assert isinstance(raised.value, telegram.TelegramPollingConflict) is (status == 409)


@pytest.mark.parametrize("delay,expected", [(1, 1), (37, 37), (3600, 3600),
                                            (0, 5), (-1, 5),
                                            (True, 5), ("12", 5), (2.5, 5), (None, 5)])
def test_rate_limit_delay_is_bounded_and_not_coerced(monkeypatch, delay, expected):
    error = http_failure(monkeypatch, 429, parameters={"retry_after": delay})
    assert (error.retry_after if error.retry_after is not None else 5) == expected


@pytest.mark.parametrize("status", [401, 409])
def test_http_error_body_read_failure_keeps_known_fatal_status(monkeypatch, status):
    class UnreadableHTTPError(urllib.error.HTTPError):
        def read(self, *args, **kwargs):
            raise TimeoutError(f"{POISON} {URL}")

    def fail(*args, **kwargs):
        raise UnreadableHTTPError(URL, status, POISON, {}, io.BytesIO())
    monkeypatch.setattr(telegram.urllib.request, "urlopen", fail)
    with pytest.raises(telegram.TelegramAPIError) as raised:
        telegram.telegram_api(TOKEN, "getUpdates")
    assert raised.value.status_code == status
    assert raised.value.retryable is False
    assert isinstance(raised.value, telegram.TelegramPollingConflict) is (status == 409)
    assert_private_content_absent(str(raised.value))


@pytest.mark.parametrize("payload", [b"not-json " + POISON.encode(), b"\xff", [],
                                     {"ok": False, "description": POISON},
                                     {"ok": True, "result": POISON}, {"ok": True},
                                     {"ok": "true", "result": []},
                                     {"ok": True, "result": [POISON]},
                                     {"ok": True, "result": [{"update_id": True}]},
                                     {"ok": True, "result": [{"update_id": -1}]},
                                     {"ok": False, "error_code": True},
                                     {"ok": False, "error_code": "401"}])
def test_invalid_response_is_safe_and_retryable(monkeypatch, payload):
    monkeypatch.setattr(telegram.urllib.request, "urlopen", lambda *a, **k: response(payload))
    with pytest.raises(telegram.TelegramAPIError) as raised:
        telegram.telegram_api(TOKEN, "getUpdates")
    assert raised.value.retryable is True
    assert_private_content_absent(str(raised.value))


@pytest.mark.parametrize("failure", [urllib.error.URLError(f"{POISON} {URL}"),
                                     TimeoutError(f"{POISON} {URL}"),
                                     OSError(f"{POISON} {URL}")])
def test_network_errors_never_echo_exception_reason(monkeypatch, failure):
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(telegram.urllib.request, "urlopen", fail)
    with pytest.raises(telegram.TelegramAPIError) as raised:
        telegram.telegram_api(TOKEN, "getUpdates")
    assert raised.value.retryable is True
    assert_private_content_absent(str(raised.value))


def test_unknown_method_does_not_echo_arbitrary_method_or_payload(monkeypatch):
    def fail(*args, **kwargs):
        raise urllib.error.URLError(f"{POISON} {URL}")
    monkeypatch.setattr(telegram.urllib.request, "urlopen", fail)
    with pytest.raises((telegram.TelegramAPIError, ValueError)) as raised:
        telegram.telegram_api(TOKEN, f"getUpdates/{POISON}", {"private": POISON})
    assert_private_content_absent(str(raised.value))


def test_successful_api_response_preserves_updates(monkeypatch):
    expected = {"ok": True, "result": [{"update_id": 0, "message": {"text": POISON}}]}
    monkeypatch.setattr(telegram.urllib.request, "urlopen", lambda *a, **k: response(expected))
    assert telegram.telegram_api(TOKEN, "getUpdates") == expected


def test_unserializable_local_payload_has_safe_fatal_diagnostic(monkeypatch):
    monkeypatch.setattr(telegram.urllib.request, "urlopen", lambda *a, **k: pytest.fail("Invalid local request must not be sent"))
    with pytest.raises(telegram.TelegramAPIError) as raised:
        telegram.telegram_api(TOKEN, "sendMessage", {POISON: object()})
    assert raised.value.retryable is False
    assert_private_content_absent(str(raised.value))


def test_debug_api_diagnostics_only_expose_operation_and_outcome(tmp_path, monkeypatch, capsys):
    log_file = tmp_path / "api-diagnostics.log"
    with telegram.configure_listener_logging(debug=True, log_file=log_file):
        error = http_failure(monkeypatch, 401)
    output = capsys.readouterr()
    text = output.out + output.err + log_file.read_text(encoding="utf-8")
    assert "getUpdates" in text and "401" in text
    assert_private_content_absent(text + str(error))


def make_bot(tmp_path, api):
    paths = {name: tmp_path / name for name in ("config.json", "profile.json", "library.sqlite3", "state.json")}
    paths["config.json"].write_text('{"synthetic": true}', encoding="utf-8")
    paths["profile.json"].write_text('{"synthetic": true}', encoding="utf-8")
    paths["library.sqlite3"].write_bytes(b"Synthetic sentinel: polling must not open the library")
    paths["state.json"].write_text('{"next_update_offset": 41}', encoding="utf-8")
    return telegram.LitRadarTelegramBot(token=TOKEN, chat_id="12345", api=api,
        config_path=paths["config.json"], profile_path=paths["profile.json"],
        db_path=paths["library.sqlite3"], state_path=paths["state.json"])


def files(directory):
    return {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob("*") if p.is_file()}


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409])
def test_fatal_poll_failure_stops_without_retry_or_data_writes(tmp_path, monkeypatch, status):
    error = http_failure(monkeypatch, status)
    calls = []
    def api(token, method, payload=None, **kwargs):
        calls.append((method, payload))
        if method == "getUpdates":
            raise error
        return {"ok": True, "result": True}
    bot = make_bot(tmp_path, api)
    before = files(tmp_path)
    monkeypatch.setattr(telegram.time, "sleep", lambda *_: pytest.fail("Fatal errors must not retry"))
    with pytest.raises(telegram.TelegramAPIError):
        bot.run_forever()
    assert len([c for c in calls if c[0] == "getUpdates"]) == 1
    assert calls[-1][1]["offset"] == 41
    assert bot.offset == 41
    assert files(tmp_path) == before


def test_rate_limit_above_automatic_wait_bound_stops_without_early_retry(tmp_path, monkeypatch):
    error = http_failure(monkeypatch, 429, parameters={"retry_after": 3601})
    assert error.status_code == 429
    assert error.retryable is False
    assert 0 < error.retry_after <= 3600
    assert_private_content_absent(str(error))
    polls = []
    def api(token, method, payload=None, **kwargs):
        if method == "getUpdates":
            polls.append(payload)
            raise error
        return {"ok": True, "result": True}
    bot = make_bot(tmp_path, api)
    before = files(tmp_path)
    monkeypatch.setattr(telegram.time, "sleep", lambda *_: pytest.fail("Must not retry before requested server delay"))
    with pytest.raises(telegram.TelegramAPIError):
        bot.run_forever()
    assert len(polls) == 1
    assert files(tmp_path) == before


@pytest.mark.parametrize("status,delay", [(429, 19), (503, 5), (None, 5)])
def test_transient_poll_retries_preserving_offset_and_interrupt_stops(tmp_path, monkeypatch, status, delay):
    if status is None:
        def fail(*args, **kwargs):
            raise urllib.error.URLError(f"{POISON} {URL}")
        monkeypatch.setattr(telegram.urllib.request, "urlopen", fail)
        with pytest.raises(telegram.TelegramAPIError) as raised:
            telegram.telegram_api(TOKEN, "getUpdates")
        error = raised.value
    else:
        error = http_failure(monkeypatch, status, parameters={"retry_after": delay})
    polls, sleeps = [], []
    def api(token, method, payload=None, **kwargs):
        if method == "getUpdates":
            polls.append(payload)
            if len(polls) == 1:
                raise error
            raise KeyboardInterrupt
        return {"ok": True, "result": True}
    bot = make_bot(tmp_path, api)
    before = files(tmp_path)
    monkeypatch.setattr(telegram.time, "sleep", sleeps.append)
    assert bot.run_forever() is None
    assert sleeps == [delay]
    assert [poll["offset"] for poll in polls] == [41, 41]
    assert files(tmp_path) == before


def test_keyboard_interrupt_during_retry_backoff_is_clean(tmp_path, monkeypatch):
    error = http_failure(monkeypatch, 503)
    def api(token, method, payload=None, **kwargs):
        if method == "getUpdates":
            raise error
        return {"ok": True, "result": True}
    bot = make_bot(tmp_path, api)
    def interrupt(*args):
        raise KeyboardInterrupt
    monkeypatch.setattr(telegram.time, "sleep", interrupt)
    assert bot.run_forever() is None


def test_menu_setup_failure_is_nonfatal_and_does_not_log_exception_text(tmp_path, capsys):
    calls = []
    def api(token, method, payload=None, **kwargs):
        calls.append(method)
        if method == "setMyCommands":
            raise RuntimeError(f"{POISON} {URL}")
        raise KeyboardInterrupt
    bot = make_bot(tmp_path, api)
    with telegram.configure_listener_logging(debug=True):
        assert bot.run_forever() is None
    output = capsys.readouterr()
    assert calls == ["setMyCommands", "getUpdates"]
    assert_private_content_absent(output.out + output.err)


def test_listener_logging_is_scoped_timestamped_and_debug_is_opt_in(tmp_path, capsys):
    logger = logging.getLogger("litradar.telegram")
    previous = (logger.handlers[:], logger.level, logger.propagate)
    with telegram.configure_listener_logging():
        logger.info("synthetic-info-marker")
        logger.debug("synthetic-debug-marker")
    output = capsys.readouterr()
    text = output.out + output.err
    assert re.search(r"\d{4}-\d{2}-\d{2}.*INFO.*synthetic-info-marker", text)
    assert "synthetic-debug-marker" not in text
    assert (logger.handlers, logger.level, logger.propagate) == previous

    log_file = tmp_path / "diagnostics.log"
    with pytest.raises(RuntimeError, match="synthetic context failure"):
        with telegram.configure_listener_logging(debug=True, log_file=log_file):
            rotating = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
            assert len(rotating) == 1
            assert rotating[0].maxBytes == 1024 * 1024 and rotating[0].backupCount == 3
            logger.debug("synthetic-debug-marker Україна")
            raise RuntimeError("synthetic context failure")
    assert "synthetic-debug-marker Україна" in log_file.read_text(encoding="utf-8")
    assert (logger.handlers, logger.level, logger.propagate) == previous
    log_file.unlink()  # All handlers must be closed, including on Windows.


@pytest.mark.parametrize("route", ["update", "callback", "command"])
def test_debug_error_paths_never_log_or_send_untrusted_exception_text(tmp_path, monkeypatch, capsys, route):
    sent = []
    message = {"update_id": 42, "message": {"chat": {"id": 12345}, "text": f"/help {POISON}"}}
    callback = {"update_id": 42, "callback_query": {"id": POISON, "data": POISON,
                "message": {"chat": {"id": 12345}}}}
    def api(token, method, payload=None, **kwargs):
        if method == "sendMessage":
            sent.append(payload["text"])
        if method == "getUpdates":
            return {"ok": True, "result": [message]}
        return {"ok": True, "result": True}
    bot = make_bot(tmp_path, api)
    def fail(*args):
        raise RuntimeError(f"{POISON} {URL}")
    monkeypatch.setattr(bot, {"update": "process_update", "callback": "_dispatch_action",
                             "command": "_dispatch_command"}[route], fail)
    log_file = tmp_path / "diagnostics.log"
    with telegram.configure_listener_logging(debug=True, log_file=log_file):
        if route == "update":
            assert bot.poll_once() == 1
            assert bot.offset == 43
        else:
            bot.process_update(callback if route == "callback" else message)
    output = capsys.readouterr()
    assert_private_content_absent(output.out + output.err + log_file.read_text(encoding="utf-8") + "".join(sent))


def test_digest_delivery_failure_persists_failed_status_without_private_error(tmp_path, monkeypatch, capsys):
    from sources.base import Paper

    replies, attempts = [], []
    def api(token, method, payload=None, **kwargs):
        if method == "sendMessage":
            replies.append(payload["text"])
        return {"ok": True, "result": True}

    bot = make_bot(tmp_path, api)
    bot.db_path.unlink()  # Replace the polling sentinel with a real disposable library.
    store = telegram.PaperStore(bot.db_path)
    try:
        paper_id = store.upsert_paper(Paper(source="fixture", external_id="digest-fixture",
                                          title="Synthetic digest paper"),
                                     relevance_score=0.1, matched_groups={})
    finally:
        store.close()
    result = SimpleNamespace(text="Synthetic digest body", generated_at="2026-10-15T10:00:00+00:00",
                             since="2026-10-14T10:00:00+00:00", paper_ids=[paper_id], warnings_count=0)
    monkeypatch.setattr(telegram, "build_digest", lambda **kwargs: result)

    def fail_delivery(text, **kwargs):
        attempts.append(text)
        raise RuntimeError(f"{POISON} {TOKEN} {URL}")
    monkeypatch.setattr(telegram, "send_telegram", fail_delivery)
    log_file = tmp_path / "digest-diagnostics.log"
    with telegram.configure_listener_logging(debug=True, log_file=log_file):
        bot._send_digest("daily")

    store = telegram.PaperStore(bot.db_path)
    try:
        deliveries = store.conn.execute("SELECT * FROM digest_deliveries").fetchall()
        assert len(deliveries) == 1
        delivery = deliveries[0]
        assert delivery["status"] == "failed"
        assert delivery["sent_at"] is None
        assert delivery["error_message"]
        assert delivery["generated_at"] == result.generated_at
        assert json.loads(delivery["paper_ids_json"]) == [paper_id]
        assert not store.conn.execute("SELECT * FROM digest_delivery_papers").fetchall()
        assert store.latest_digest_sent_at("telegram") is None
    finally:
        store.close()
    assert attempts == [result.text]
    assert len(replies) == 2 and "❌" in replies[-1]
    assert not any("✅" in reply for reply in replies)
    output = capsys.readouterr()
    assert_private_content_absent(delivery["error_message"] + "".join(replies)
                                 + output.out + output.err + log_file.read_text(encoding="utf-8"))
