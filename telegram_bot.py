"""Interactive, single-user Telegram command loop for LitBeacon (legacy module name: LitRadar).

The loop uses Telegram long polling. Scheduled digests do not depend on this
process; commands and inline buttons do. Only the configured chat ID is allowed.
"""
from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from research_digest import (
    DEFAULT_DB,
    DEFAULT_PROFILE,
    DEFAULT_SCAN_CONFIG,
    _iso,
    _split_message,
    _now,
    build_digest,
    run_scheduled_scan,
    send_telegram,
)
from storage.sqlite import PaperStore

from litradar_runtime import WORKSPACE_ROOT, CODE_ROOT

ROOT = WORKSPACE_ROOT
DEFAULT_STATE = ROOT / "data" / "telegram_bot_state.json"
MAX_TOPIC_QUERIES = 10
MAX_QUERY_CHARS = 200
MAX_API_BYTES = 4 * 1024 * 1024
LOGGER = logging.getLogger("litradar.telegram")
_METHODS = {"getUpdates", "sendMessage", "setMyCommands", "answerCallbackQuery"}
_FORMATTER = logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z")


@contextmanager
def configure_listener_logging(*, debug: bool = False, log_file: str | Path | None = None):
    """Configure only this listener's logger; restore caller state on every exit."""
    previous = (list(LOGGER.handlers), LOGGER.level, LOGGER.propagate, LOGGER.disabled)
    owned = []
    try:
        console = logging.StreamHandler(sys.stderr)
        owned.append(console)
        if log_file is not None:
            owned.append(RotatingFileHandler(log_file, mode="a", maxBytes=1024 * 1024,
                                             backupCount=3, encoding="utf-8", errors="backslashreplace"))
        for handler in owned:
            handler.setLevel(logging.DEBUG if debug else logging.INFO)
            handler.setFormatter(_FORMATTER)
        LOGGER.handlers = owned[:]
        LOGGER.setLevel(logging.DEBUG if debug else logging.INFO)
        LOGGER.propagate = False
        LOGGER.disabled = False
        yield LOGGER
    finally:
        LOGGER.handlers, level, LOGGER.propagate, LOGGER.disabled = previous
        LOGGER.setLevel(level)
        for handler in owned:
            handler.close()


def _log(level: int, message: str, *args) -> None:
    if LOGGER.handlers:
        LOGGER.log(level, message, *args)
    elif level >= logging.INFO:
        # No implicit file/global logging configuration outside the CLI context.
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_FORMATTER)
        try:
            handler.handle(LOGGER.makeRecord(LOGGER.name, level, __file__, 0, message, args, None))
        finally:
            handler.close()


def _safe_status(value) -> int | None:
    return value if type(value) is int and 100 <= value <= 599 else None


def _retry_delay(value) -> int:
    if type(value) is int and value > 3600:
        return 3600
    return value if type(value) is int and 1 <= value <= 3600 else 5


def _diagnostic(method: str, status_code: int | None, outcome: str) -> str:
    method = method if method in _METHODS else "request"
    prefix = f"Telegram {method}"
    if status_code == 429 and outcome == "retry_limit":
        return f"{prefix}: rate limited (429). Requested wait exceeds the automatic retry limit; retry manually later."
    messages = {
        400: "request rejected (400). Check the local bot/chat configuration and request settings.",
        401: "authentication failed (401). Check the bot token locally; do not share it in logs.",
        403: "access denied (403). Check bot permissions, allowed chat settings and whether the bot is blocked.",
        404: "endpoint not found (404). Check the bot token and installation locally.",
        409: ("polling conflict (409). Another listener or a configured webhook may own updates. Stop duplicate listeners or review the webhook manually; no webhook was changed."
              if method == "getUpdates" else "request conflict (409). Review bot state and request settings before retrying."),
        429: "rate limited (429). Wait for the bounded retry interval before trying again.",
    }
    if status_code in messages:
        return f"{prefix}: {messages[status_code]}"
    if status_code is not None:
        if status_code >= 500:
            return f"{prefix}: service unavailable ({status_code}). Retry later."
        return f"{prefix}: unexpected API status ({status_code}). Review the local configuration before retrying."
    descriptions = {
        "timeout": "connection timed out. Check connectivity and retry.",
        "dns": "name resolution failed. Check DNS/network settings and retry.",
        "tls": "secure connection failed. Check certificate trust and system time; do not disable TLS verification.",
        "network": "network/proxy connection failed. Check connectivity and proxy settings and retry.",
        "json": "returned invalid JSON. Check connectivity/proxy settings and retry.",
        "payload": "returned an invalid API payload. Retry later or check the installation.",
        "method": "unsupported API method. Review the local installation.",
        "local": "local request preparation failed. Review the local configuration.",
    }
    return f"{prefix}: {descriptions.get(outcome, 'API request rejected. Review the local configuration.')}"


class TelegramAPIError(RuntimeError):
    """Typed, fixed-text diagnostics; public supplied messages are never echoed."""
    def __init__(self, message=None, *, status_code=None, retry_after=None,
                 retryable: bool = False, method="getUpdates", outcome="api"):
        self.status_code = _safe_status(status_code)
        self.retry_after = _retry_delay(retry_after)
        retry_limit = self.status_code == 429 and type(retry_after) is int and retry_after > 3600
        self.retryable = retryable is True and not retry_limit
        self.method = method if isinstance(method, str) and method in _METHODS else "request"
        self.outcome = outcome if isinstance(outcome, str) and outcome in {
            "api", "timeout", "dns", "tls", "network", "json", "payload", "method", "local", "retry_limit"} else "api"
        if retry_limit:
            self.outcome = "retry_limit"
        super().__init__(_diagnostic(self.method, self.status_code, self.outcome))


class TelegramPollingConflict(TelegramAPIError):
    def __init__(self, message=None, *, status_code=409, retry_after=None,
                 retryable=False, method="getUpdates", outcome="api"):
        super().__init__(status_code=409, retry_after=retry_after, retryable=False,
                         method="getUpdates", outcome="api")


def listener_error_message(exc: BaseException) -> str:
    """Never render unknown exception messages, class names, URLs or payloads."""
    if type(exc) in {TelegramAPIError, TelegramPollingConflict}:
        return _diagnostic(exc.method, _safe_status(exc.status_code), exc.outcome)
    return "Unexpected local error; review setup."


def _api_error(method, *, status_code=None, retry_after=None, outcome="api"):
    status_code = _safe_status(status_code)
    retry_limit = status_code == 429 and type(retry_after) is int and retry_after > 3600
    if retry_limit:
        outcome = "retry_limit"
    cls = TelegramPollingConflict if method == "getUpdates" and status_code == 409 else TelegramAPIError
    return cls(status_code=status_code, retry_after=retry_after,
               retryable=not retry_limit and (status_code == 429 or (status_code is not None and status_code >= 500)
               or (status_code is None and outcome in {"timeout", "dns", "tls", "network", "json", "payload"})),
               method=method, outcome=outcome)


def _network_outcome(exc) -> str:
    reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(reason, socket.gaierror):
        return "dns"
    if isinstance(reason, ssl.SSLError):
        return "tls"
    return "network"


def _read_api_json(response):
    try:
        raw = response.read(MAX_API_BYTES + 1)
        if len(raw) > MAX_API_BYTES:
            return None, "payload"
        return json.loads(raw.decode("utf-8")), None
    except (ValueError, UnicodeError, RecursionError):
        return None, "json"


def _response_error(method, data, *, status_code=None):
    if isinstance(data, dict):
        if status_code is None:
            status_code = _safe_status(data.get("error_code"))
        parameters = data.get("parameters")
        retry_after = parameters.get("retry_after") if isinstance(parameters, dict) else None
    else:
        retry_after = None
    return _api_error(method, status_code=status_code, retry_after=retry_after,
                      outcome="api" if status_code is not None else "payload")

BOT_COMMANDS = [
    {"command": "start", "description": "Show LitBeacon menu"},
    {"command": "help", "description": "Show available commands"},
    {"command": "digest", "description": "Send a daily or weekly digest"},
    {"command": "schedule", "description": "View/change/remove scheduled jobs"},
    {"command": "jobs", "description": "See or remove scan/digest jobs"},
    {"command": "settings", "description": "Show digest settings"},
    {"command": "scan", "description": "Run configured searches now"},
    {"command": "topics", "description": "List saved search topics"},
    {"command": "topic", "description": "Add or remove a search topic"},
    {"command": "search", "description": "Search the local library"},
    {"command": "recent", "description": "Show recently added papers"},
    {"command": "queue", "description": "View or size the reading queue"},
    {"command": "limit", "description": "Set papers per digest (1–30)"},
    {"command": "overlap", "description": "Turn overlap warnings on/off"},
    {"command": "stats", "description": "Show library statistics"},
]


def telegram_api(token: str, method: str, payload: dict[str, Any] | None = None, *, timeout: int = 35) -> dict[str, Any]:
    """Call an allowlisted Bot API method with bounded, content-free diagnostics."""
    if not token:
        raise ValueError("Telegram bot token is not configured")
    if not isinstance(method, str) or method not in _METHODS:
        raise _api_error("request", outcome="method")
    started = time.monotonic()
    status = None
    outcome = "local"
    _log(logging.DEBUG, "API method=%s outcome=started", method)
    try:
        try:
            body = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8")
            request = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=body,
                                             headers={"Content-Type": "application/json"}, method="POST")
        except (ValueError, TypeError, UnicodeError):
            raise _api_error(method, outcome="local") from None
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data, invalid = _read_api_json(response)
        except urllib.error.HTTPError as exc:
            known_status = _safe_status(exc.code)
            data = None
            try:
                try:
                    data, invalid = _read_api_json(exc)
                except Exception:
                    # HTTP status remains authoritative if its optional JSON
                    # body cannot be read; never turn 409/401 into a retry.
                    pass
            finally:
                try:
                    exc.close()
                except Exception:
                    pass
            raise _response_error(method, data, status_code=known_status) from None
        except (urllib.error.URLError, OSError) as exc:
            raise _api_error(method, outcome=_network_outcome(exc)) from None
        if invalid:
            raise _api_error(method, outcome=invalid)
        if not isinstance(data, dict) or type(data.get("ok")) is not bool:
            raise _api_error(method, outcome="payload")
        if data["ok"] is False:
            raise _response_error(method, data)
        result = data.get("result")
        valid = "result" in data
        if method == "getUpdates":
            valid = valid and isinstance(result, list) and all(
                isinstance(item, dict) and type(item.get("update_id")) is int and item["update_id"] >= 0
                for item in result)
        elif method == "sendMessage":
            valid = valid and isinstance(result, dict)
        else:
            valid = valid and type(result) is bool
        if not valid:
            raise _api_error(method, outcome="payload")
        outcome, status = "success", 200
        return data
    except TelegramAPIError as exc:
        outcome, status = exc.outcome, exc.status_code
        raise
    except (urllib.error.URLError, OSError) as exc:
        outcome = _network_outcome(exc)
        raise _api_error(method, outcome=outcome) from None
    except Exception:
        # Unexpected adapter/local failures must not expose request-bearing
        # exceptions through CLI callers, even outside the logging context.
        outcome = "local"
        raise _api_error(method, outcome=outcome) from None
    finally:
        _log(logging.DEBUG, "API method=%s outcome=%s status=%s duration_ms=%d", method, outcome,
             status if status is not None else "none", max(0, int((time.monotonic() - started) * 1000)))


def _read_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Configuration not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {config_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("digest_config.json must contain a JSON object")
    return raw


def _write_config(path: str | Path, payload: dict[str, Any]) -> None:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    temp = config_path.with_suffix(config_path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, config_path)


def _delivery_settings(config: dict[str, Any]) -> dict[str, Any]:
    delivery = config.get("delivery")
    if not isinstance(delivery, dict):
        delivery = {}
    frequency = str(delivery.get("frequency", "weekly")).casefold()
    if frequency not in {"daily", "weekly"}:
        frequency = "weekly"
    when = str(delivery.get("time", "09:00"))
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", when):
        when = "09:00"
    return {"frequency": frequency, "time": when}


def _make_keyboard() -> dict[str, Any]:
    return {"inline_keyboard": [
        [
            {"text": "📬 Daily digest", "callback_data": "digest:daily"},
            {"text": "🗓 Weekly digest", "callback_data": "digest:weekly"},
        ],
        [
            {"text": "🔎 Run scan", "callback_data": "scan"},
            {"text": "📚 Reading queue", "callback_data": "queue"},
        ],
        [
            {"text": "⚙ Settings", "callback_data": "settings"},
            {"text": "🗓 Scheduled jobs", "callback_data": "jobs"},
            {"text": "📊 Library stats", "callback_data": "stats"},
        ],
    ]}


class LitRadarTelegramBot:
    def __init__(
        self,
        *,
        token: str,
        chat_id: str,
        config_path: str | Path = DEFAULT_SCAN_CONFIG,
        db_path: str | Path = DEFAULT_DB,
        profile_path: str | Path = DEFAULT_PROFILE,
        state_path: str | Path = DEFAULT_STATE,
        api: Callable[..., dict[str, Any]] = telegram_api,
        schedule_runner: Callable[[str, str], tuple[bool, str]] | None = None,
        schedule_remover: Callable[[str], tuple[bool, str]] | None = None,
        scan_runner: Callable[..., Any] = run_scheduled_scan,
    ) -> None:
        self.token = token.strip()
        self.chat_id = str(chat_id).strip()
        if not self.token or not self.chat_id:
            raise ValueError("Set LITRADAR_TELEGRAM_BOT_TOKEN and LITRADAR_TELEGRAM_CHAT_ID in .env first")
        self.config_path = Path(config_path)
        self.db_path = Path(db_path)
        self.profile_path = Path(profile_path)
        self.state_path = Path(state_path)
        self.api = api
        self.schedule_runner = schedule_runner
        self.schedule_remover = schedule_remover
        self.scan_runner = scan_runner
        self.offset = self._load_offset()

    def _load_offset(self) -> int | None:
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
            offset = state.get("next_update_offset") if isinstance(state, dict) else None
            return int(offset) if offset is not None and int(offset) >= 0 else None
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def _save_offset(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temp.write_text(json.dumps({"next_update_offset": self.offset}, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, self.state_path)

    def _send(self, text: str, *, keyboard: dict[str, Any] | None = None) -> None:
        chunks = _split_message(text, 3500)
        for index, chunk in enumerate(chunks):
            payload: dict[str, Any] = {
                "chat_id": self.chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            }
            if keyboard is not None and index == len(chunks) - 1:
                payload["reply_markup"] = keyboard
            self.api(self.token, "sendMessage", payload)

    def _set_commands(self) -> None:
        # Convenience only: command handling still works if Telegram rejects menu setup.
        try:
            self.api(self.token, "setMyCommands", {"commands": BOT_COMMANDS})
        except Exception as exc:
            _log(logging.WARNING, "Telegram command menu unavailable; commands remain usable. %s", listener_error_message(exc))

    def poll_once(self, *, timeout: int = 10) -> int:
        wait = min(max(int(timeout), 0), 25)
        payload: dict[str, Any] = {"timeout": wait, "allowed_updates": ["message", "callback_query"]}
        if self.offset is not None:
            payload["offset"] = self.offset
        response = self.api(self.token, "getUpdates", payload, timeout=wait + 10)
        if not isinstance(response, dict) or response.get("ok") is not True or not isinstance(response.get("result"), list):
            raise _api_error("getUpdates", outcome="payload")
        updates = response["result"]
        _log(logging.DEBUG, "Polling outcome=received update_count=%d", len(updates))
        processed = 0
        for update in updates:
            try:
                self.process_update(update)
            except Exception as exc:
                # Never stall the queue or render untrusted exception details.
                _log(logging.WARNING, "Telegram update failed. %s", listener_error_message(exc))
            finally:
                try:
                    self.offset = max(int(self.offset or 0), int(update["update_id"]) + 1)
                    self._save_offset()
                except (KeyError, ValueError, TypeError):
                    pass
            processed += 1
        return processed

    def run_forever(self, *, timeout: int = 25) -> None:
        try:
            self._set_commands()
            _log(logging.INFO, "LitBeacon Telegram bot is listening. Press Ctrl+C to stop.")
            _log(logging.INFO, "Scheduled digest delivery continues independently of this listener.")
            while True:
                try:
                    self.poll_once(timeout=timeout)
                except TelegramAPIError as exc:
                    if not exc.retryable:
                        _log(logging.ERROR, "Telegram listener stopped. %s", listener_error_message(exc))
                        raise
                    delay = _retry_delay(exc.retry_after)
                    _log(logging.WARNING, "Telegram polling failed; retrying in %d seconds. %s", delay, listener_error_message(exc))
                    time.sleep(delay)
                except Exception as exc:
                    _log(logging.WARNING, "Telegram polling failed; retrying in 5 seconds. %s", listener_error_message(exc))
                    time.sleep(5)
        except KeyboardInterrupt:
            _log(logging.INFO, "LitBeacon Telegram bot stopped.")
            return

    def process_update(self, update: dict[str, Any]) -> None:
        callback = update.get("callback_query")
        if isinstance(callback, dict):
            message = callback.get("message") or {}
            chat = message.get("chat") or {}
            if str(chat.get("id", "")) != self.chat_id:
                self.api(self.token, "answerCallbackQuery", {"callback_query_id": callback.get("id"), "text": "This bot is private."})
                return
            self.api(self.token, "answerCallbackQuery", {"callback_query_id": callback.get("id")})
            try:
                self._dispatch_action(str(callback.get("data") or ""))
            except Exception as exc:
                _log(logging.WARNING, "Telegram callback failed. %s", listener_error_message(exc))
                try:
                    self._send(f"Не вдалося виконати дію. {listener_error_message(exc)}")
                except Exception:
                    pass
            return

        message = update.get("message") or update.get("channel_post") or {}
        chat = message.get("chat") or {}
        if str(chat.get("id", "")) != self.chat_id:
            return  # single-user bot: ignore all chats except the configured allowlist
        text = str(message.get("text") or "").strip()
        if not text.startswith("/"):
            return
        command_text = text.split(maxsplit=1)
        command = command_text[0].split("@", 1)[0].casefold().lstrip("/")
        argument = command_text[1].strip() if len(command_text) > 1 else ""
        try:
            self._dispatch_command(command, argument)
        except Exception as exc:
            _log(logging.WARNING, "Telegram command failed. %s", listener_error_message(exc))
            try:
                self._send(f"Не вдалося виконати команду. {listener_error_message(exc)}")
            except Exception:
                pass

    def _dispatch_action(self, data: str) -> None:
        if data.startswith("digest:"):
            period = data.split(":", 1)[1]
            self._send_digest(period)
        elif data == "scan":
            self._run_scan()
        elif data == "queue":
            self._show_queue()
        elif data == "settings":
            self._show_settings()
        elif data == "stats":
            self._show_stats()
        elif data == "jobs":
            self._set_or_show_schedule("")

    def _dispatch_command(self, command: str, argument: str) -> None:
        if command in {"start", "menu"}:
            self._send(
                "Вітаю! 👋\nЯ LitBeacon — твій локальний науковий помічник (раніше LitRadar).\n\n"
                "Можу надсилати дайджести, запускати пошук і допомагати керувати чергою читання.\n"
                "Вибери дію або надішли /help. Для керування фоновими завданнями — /jobs.",
                keyboard=_make_keyboard(),
            )
        elif command in {"help", "commands"}:
            self._send(
                "Команди LitBeacon (раніше LitRadar)\n"
                "/digest [daily|weekly] — сформувати й надіслати дайджест\n"
                "/schedule або /jobs — переглянути стан; /schedule daily 08:00 або /schedule weekly 09:00 — змінити час\n"
                "/schedule remove scan|digest|all — вимкнути вибрані автоматичні завдання\n"
                "/settings — налаштування дайджесту\n"
                "/scan — запустити налаштовані пошуки зараз\n"
                "/topics — список пошукових тем\n"
                "/topic add NAME | QUERY — додати тему; /topic remove NAME — видалити\n"
                "/search QUERY — шукати в локальній бібліотеці\n"
                "/recent — нещодавно додані роботи\n"
                "/queue [0–10] — перегляд черги або налаштування її розміру в дайджесті\n"
                "/limit 1–30 — максимум нових робіт у дайджесті\n"
                "/overlap on|off — вмикати/вимикати попередження про схожі роботи\n"
                "/stats — статистика локальної бібліотеки\n"
                "\nКоманди керування доступні лише в чаті, вказаному в .env. Для команд і кнопок має працювати окрема сесія run_telegram_bot.bat. Автоматичні заплановані дайджести працюють незалежно від цієї сесії."
            )
        elif command in {"settings", "config"}:
            self._show_settings()
        elif command in {"schedule", "jobs"}:
            self._set_or_show_schedule(argument)
        elif command == "digest":
            config = _read_config(self.config_path)
            default_period = _delivery_settings(config)["frequency"]
            period = argument.casefold() or default_period
            if period not in {"daily", "weekly"}:
                self._send("Використання: /digest daily або /digest weekly")
            else:
                self._send_digest(period)
        elif command == "scan":
            self._run_scan()
        elif command in {"topics", "queries"}:
            self._show_topics()
        elif command == "topic":
            self._edit_topic(argument)
        elif command == "search":
            self._search_library(argument)
        elif command == "recent":
            self._show_recent()
        elif command == "queue":
            if argument:
                try:
                    limit = int(argument)
                except ValueError:
                    self._send("Використання: /queue [0–10]")
                    return
                self._set_numeric_setting("queue_limit", limit, 0, 10)
            else:
                self._show_queue()
        elif command == "limit":
            try:
                self._set_numeric_setting("limit", int(argument), 1, 30)
            except ValueError:
                self._send("Використання: /limit 1–30")
        elif command == "overlap":
            value = argument.casefold()
            if value not in {"on", "off"}:
                self._send("Використання: /overlap on або /overlap off")
            else:
                config = _read_config(self.config_path)
                digest = config.setdefault("digest", {})
                digest["include_overlap"] = value == "on"
                _write_config(self.config_path, config)
                self._send(f"Попередження про можливий перетин тем: {'увімкнено' if value == 'on' else 'вимкнено'}.")
        elif command in {"stats", "status"}:
            self._show_stats()
        else:
            self._send("Не знаю такої команди. Напиши /help або вибери дію в меню.")

    def _show_settings(self) -> None:
        config = _read_config(self.config_path)
        delivery = _delivery_settings(config)
        digest = config.get("digest", {}) if isinstance(config.get("digest"), dict) else {}
        overlap = bool(digest.get("include_overlap", True))
        queries = config.get("queries", [])
        self._send(
            "⚙ Налаштування LitBeacon\n"
            f"Розклад: {delivery['frequency']} о {delivery['time']} (щотижня — неділя)\n"
            f"Нових робіт у дайджесті: {int(digest.get('limit', 15))}\n"
            f"Черга читання: {int(digest.get('queue_limit', 5))}\n"
            f"Попередження про перетини: {'on' if overlap else 'off'}\n"
            f"Пошукових тем: {len(queries) if isinstance(queries, list) else 0}\n\n"
            "Змінити розклад: /schedule daily 08:00 або /schedule weekly 09:00\n"
            "Вимкнути job: /schedule remove scan|digest|all\n"
            "Інші параметри: /limit 10, /queue 5, /overlap off, /topics",
            keyboard=_make_keyboard(),
        )

    def _set_or_show_schedule(self, argument: str) -> None:
        config = _read_config(self.config_path)
        current = _delivery_settings(config)
        if not argument:
            delivery_enabled = config.get("delivery", {}).get("enabled", True)
            scan_enabled = config.get("scan", {}).get("enabled", True)
            self._send(
                f"Автоматичне сканування: {'увімкнено' if scan_enabled else 'вимкнено'}\n"
                f"Автоматичний дайджест: {'увімкнено' if delivery_enabled else 'вимкнено'}; "
                f"{current['frequency']} о {current['time']} (weekly — щонеділі).\n\n"
                "Змінити час: /schedule daily 08:00 або /schedule weekly 09:00\n"
                "Вимкнути завдання: /schedule remove scan, /schedule remove digest або /schedule remove all"
            )
            return
        parts = argument.split()
        if len(parts) == 2 and parts[0].casefold() in {"remove", "delete", "disable"}:
            job = parts[1].casefold()
            if job not in {"scan", "digest", "all"}:
                self._send("Використання: /schedule remove scan|digest|all")
                return
            success, message = self._remove_scheduled_jobs(job)
            if not success:
                self._send(f"Не вдалося вимкнути завдання: {message}")
                return
            if job in {"scan", "all"}:
                config.setdefault("scan", {})["enabled"] = False
            if job in {"digest", "all"}:
                config.setdefault("delivery", {})["enabled"] = False
            _write_config(self.config_path, config)
            self._send(f"✅ Завдання вимкнено: {job}. {message}")
            return
        if len(parts) != 2 or parts[0].casefold() not in {"daily", "weekly"} or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", parts[1]):
            self._send(
                "Використання:\n/schedule daily 08:00\n/schedule weekly 09:00\n"
                "/schedule remove scan|digest|all\nЧас — локальний час Windows, формат HH:MM."
            )
            return
        frequency, when = parts[0].casefold(), parts[1]
        success, message = self._reschedule(frequency, when)
        if not success:
            self._send(f"Не вдалося оновити Windows Task Scheduler: {message}")
            return
        config.setdefault("delivery", {})
        config["delivery"].update({"frequency": frequency, "time": when, "enabled": True})
        _write_config(self.config_path, config)
        if os.name == "nt" or self.schedule_runner is not None:
            extra = message or "Windows Task Scheduler оновлено."
        else:
            extra = "Налаштування збережено; на цій ОС онови cron/launchd окремо."
        self._send(f"✅ Розклад оновлено: {frequency} о {when}. {extra}")

    def _reschedule(self, frequency: str, when: str) -> tuple[bool, str]:
        if self.schedule_runner is not None:
            return self.schedule_runner(frequency, when)
        if os.name != "nt":
            return True, ""
        command = [sys.executable, str(CODE_ROOT / "cli.py"), "schedule", "install", "--job", "digest", "--frequency", frequency, "--time", when]
        try:
            completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=45, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return False, "Scheduler operation failed; review the local setup."
        if completed.returncode:
            detail = (completed.stderr or completed.stdout or "scheduler rejected the request").strip()
            return False, detail[-500:]
        detail = (completed.stdout or "").strip()
        return True, detail[-350:]

    def _remove_scheduled_jobs(self, job: str) -> tuple[bool, str]:
        if self.schedule_remover is not None:
            return self.schedule_remover(job)
        command = [sys.executable, str(CODE_ROOT / "cli.py"), "schedule", "remove", "--job", job]
        try:
            completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=45, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return False, "Scheduler operation failed; review the local setup."
        detail = (completed.stdout or completed.stderr or "").strip()
        if completed.returncode:
            return False, detail[-500:] or f"exit code {completed.returncode}"
        return True, detail[-350:]

    def _set_numeric_setting(self, key: str, value: int, lower: int, upper: int) -> None:
        if not lower <= value <= upper:
            self._send(f"Значення має бути в межах {lower}–{upper}.")
            return
        config = _read_config(self.config_path)
        digest = config.setdefault("digest", {})
        digest[key] = value
        _write_config(self.config_path, config)
        labels = {"limit": "Максимум нових робіт у дайджесті", "queue_limit": "Робіт у секції черги читання"}
        self._send(f"✅ {labels.get(key, key)}: {value}.")

    def _edit_topic(self, argument: str) -> None:
        parts = argument.split(maxsplit=1)
        if len(parts) < 2 or parts[0].casefold() not in {"add", "remove"}:
            self._send("Використання:\n/topic add NAME | пошуковий запит\n/topic remove NAME")
            return
        action, value = parts[0].casefold(), parts[1].strip()
        config = _read_config(self.config_path)
        queries = config.setdefault("queries", [])
        if not isinstance(queries, list):
            self._send("Некоректна конфігурація queries у digest_config.json.")
            return
        if action == "add":
            if "|" not in value:
                self._send("Потрібен роздільник |. Приклад: /topic add irony | contextual irony detection")
                return
            name, query = (part.strip() for part in value.split("|", 1))
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}", name):
                self._send("Назва теми: 1–40 символів, латиниця/цифри/_/-. Запит може бути українською чи англійською.")
                return
            if not query or len(query) > MAX_QUERY_CHARS:
                self._send(f"Пошуковий запит має містити 1–{MAX_QUERY_CHARS} символів.")
                return
            if len(queries) >= MAX_TOPIC_QUERIES:
                self._send(f"Ліміт досягнуто: максимум {MAX_TOPIC_QUERIES} пошукових тем. Видали одну через /topic remove NAME.")
                return
            if any(isinstance(item, dict) and str(item.get("name", "")).casefold() == name.casefold() for item in queries):
                self._send(f"Тема {name!r} вже існує. Використай іншу назву або відредагуй digest_config.json вручну.")
                return
            source_defaults = next(
                (item.get("sources") for item in queries if isinstance(item, dict) and item.get("sources")),
                ["openalex", "semantic_scholar", "arxiv"],
            )
            if isinstance(source_defaults, str):
                source_defaults = [part.strip() for part in source_defaults.split(",") if part.strip()]
            per_source_default = next(
                (int(item.get("per_source", 10)) for item in queries if isinstance(item, dict) and item.get("per_source")),
                10,
            )
            queries.append({
                "name": name,
                "query": query,
                "sources": list(source_defaults),
                "per_source": min(max(per_source_default, 1), 10),
            })
            _write_config(self.config_path, config)
            self._send(f"✅ Додано тему {name!r}. Вона братиме участь у наступному scan.\n/topics — переглянути всі теми.")
        else:
            found = next((item for item in queries if isinstance(item, dict) and str(item.get("name", "")).casefold() == value.casefold()), None)
            if found is None:
                self._send(f"Не знайдено тему {value!r}. Переглянь список командою /topics.")
                return
            if len(queries) <= 1:
                self._send("Має залишитися хоча б одна тема пошуку.")
                return
            queries.remove(found)
            _write_config(self.config_path, config)
            self._send(f"✅ Видалено тему {value!r}.")

    def _show_topics(self) -> None:
        config = _read_config(self.config_path)
        queries = config.get("queries", [])
        if not queries:
            self._send("Пошукових тем не налаштовано.")
            return
        lines = [f"Пошукові теми ({len(queries)}/{MAX_TOPIC_QUERIES})", ""]
        for item in queries:
            if not isinstance(item, dict):
                continue
            lines.append(f"• {item.get('name', 'unnamed')}: {item.get('query', '')} (до {item.get('per_source', 20)}/джерело)")
        lines.extend(["", "Додати: /topic add NAME | SEARCH QUERY", "Видалити: /topic remove NAME"])
        self._send("\n".join(lines))

    def _send_digest(self, period: str) -> None:
        if period not in {"daily", "weekly"}:
            self._send("Період має бути daily або weekly.")
            return
        self._send(f"Готую {period} дайджест із локальної бібліотеки…")
        config = _read_config(self.config_path)
        digest_settings = config.get("digest", {}) if isinstance(config.get("digest"), dict) else {}
        store = PaperStore(self.db_path)
        result = None
        try:
            result = build_digest(
                db_path=self.db_path,
                period=period,
                limit=int(digest_settings.get("limit", 15)),
                queue_limit=int(digest_settings.get("queue_limit", 5)),
                config_path=self.config_path,
                channel="telegram",
            )
            status = "sent"
            sent_at = None
            error = ""
            try:
                count = send_telegram(result.text, token=self.token, chat_id=self.chat_id)
                sent_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            except Exception as exc:
                status, error, count = "failed", listener_error_message(exc), 0
                _log(logging.WARNING, "Telegram digest delivery failed. %s", error)
            store.record_digest_delivery(
                channel="telegram", period=period, generated_at=result.generated_at, sent_at=sent_at,
                since_at=result.since, paper_ids=result.paper_ids, output_path="", status=status, error_message=error,
            )
        finally:
            store.close()
        if status == "sent":
            self._send(f"✅ {period.capitalize()} digest надіслано ({count} повідомлень). Нових робіт: {len(result.paper_ids)}; сигналів можливого перетину: {result.warnings_count}.", keyboard=_make_keyboard())
        else:
            self._send(f"❌ Не вдалося надіслати дайджест: {error}")

    def _run_scan(self) -> None:
        self._send("🔎 Запускаю всі налаштовані пошукові теми. Це може зайняти кілька хвилин…")
        result = self.scan_runner(db_path=self.db_path, profile_path=self.profile_path, config_path=self.config_path)
        self._send(
            f"✅ Сканування завершено.\nТем: {result.query_count}; отримано результатів: {result.fetched}; нових робіт: {result.newly_stored}; у бібліотеці: {result.library_total}."
            + ("\n\nПопередження:\n" + "\n".join(f"• {item[:180]}" for item in result.errors[:4]) if result.errors else ""),
            keyboard=_make_keyboard(),
        )

    def _show_queue(self) -> None:
        config = _read_config(self.config_path)
        digest = config.get("digest", {}) if isinstance(config.get("digest"), dict) else {}
        store = PaperStore(self.db_path)
        try:
            rows = store.list_papers(limit=10, status="to-read", sort="relevance_score")
            total = store.total_count(status="to-read")
        finally:
            store.close()
        lines = [f"📚 Черга читання: {total} робіт; показано {len(rows)}", ""]
        for row in rows:
            lines.append(f"#{row['id']} · {str(row['title'])[:140]} (score {float(row['relevance_score']):.2f})")
        lines.extend(["", f"У дайджесті показується до {int(digest.get('queue_limit', 5))} робіт.", "Змінити: /queue 5 (допустимо 0–10)."])
        self._send("\n".join(lines), keyboard=_make_keyboard())

    def _show_recent(self) -> None:
        store = PaperStore(self.db_path)
        try:
            rows = store.list_papers(limit=8, sort="newest_added")
        finally:
            store.close()
        if not rows:
            self._send("Бібліотека порожня.")
            return
        lines = ["🆕 Нещодавно додані роботи", ""]
        for row in rows:
            link = row["doi"] or row["url"] or "посилання немає"
            lines.append(f"#{row['id']} · {str(row['title'])[:130]}\n  score {float(row['relevance_score']):.2f} · {link}")
        self._send("\n\n".join(lines))

    def _search_library(self, query: str) -> None:
        if not query:
            self._send("Використання: /search слова для пошуку")
            return
        store = PaperStore(self.db_path)
        try:
            rows = store.list_papers(limit=8, query=query, sort="relevance_score")
        finally:
            store.close()
        if not rows:
            self._send("У локальній бібліотеці збігів не знайдено.")
            return
        lines = [f"🔎 Результати локального пошуку: {query!r}", ""]
        for row in rows:
            link = row["doi"] or row["url"] or "посилання немає"
            lines.append(f"#{row['id']} · {str(row['title'])[:140]}\n  score {float(row['relevance_score']):.2f} · {link}")
        self._send("\n\n".join(lines))

    def _show_stats(self) -> None:
        store = PaperStore(self.db_path)
        try:
            total = store.total_count()
            new = store.total_count(status="new")
            to_read = store.total_count(status="to-read")
            read = store.total_count(status="read")
        finally:
            store.close()
        config = _read_config(self.config_path)
        delivery = _delivery_settings(config)
        self._send(
            "📊 LitBeacon — статистика\n"
            f"У бібліотеці: {total}\nНові: {new}\nУ черзі читання: {to_read}\nПрочитані: {read}\n"
            f"Дайджест: {delivery['frequency']} о {delivery['time']}\n"
            f"Активних пошукових тем: {len(config.get('queries', [])) if isinstance(config.get('queries'), list) else 0}",
            keyboard=_make_keyboard(),
        )
