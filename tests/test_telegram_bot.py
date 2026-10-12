from __future__ import annotations

import json
from pathlib import Path

from storage.sqlite import PaperStore
from telegram_bot import LitRadarTelegramBot, telegram_api


def _config(path: Path) -> Path:
    path.write_text(json.dumps({
        "name": "test",
        "queries": [
            {"name": "context", "query": "adaptive context", "sources": ["openalex"], "per_source": 5}
        ],
        "scan": {"semantic": False},
        "digest": {"limit": 15, "queue_limit": 5, "include_overlap": True},
        "overlap": {"candidates": 100, "min_similarity": 0.25, "title_similarity": 0.45},
        "delivery": {"frequency": "weekly", "time": "09:00"},
    }), encoding="utf-8")
    return path


class FakeAPI:
    def __init__(self, updates=None):
        self.calls = []
        self.updates = updates or []

    def __call__(self, token, method, payload=None, *, timeout=35):
        self.calls.append((method, payload or {}, timeout))
        if method == "getUpdates":
            return {"ok": True, "result": self.updates}
        return {"ok": True, "result": {"message_id": len(self.calls)}}


def _bot(tmp_path: Path, api=None, schedule_runner=None) -> LitRadarTelegramBot:
    config = _config(tmp_path / "digest_config.json")
    return LitRadarTelegramBot(
        token="fake-token",
        chat_id="12345",
        config_path=config,
        db_path=tmp_path / "library.sqlite3",
        profile_path=tmp_path / "profile.json",
        state_path=tmp_path / "data" / "telegram_bot_state.json",
        api=api or FakeAPI(),
        schedule_runner=schedule_runner,
    )


def _message(text: str, chat_id: int = 12345, update_id: int = 1):
    return {"update_id": update_id, "message": {"message_id": update_id, "chat": {"id": chat_id, "type": "private"}, "text": text}}


def test_command_updates_schedule_and_persists_safe_config(tmp_path: Path):
    schedule_calls = []
    def schedule_runner(frequency, when):
        schedule_calls.append((frequency, when))
        return True, "Task Scheduler updated"
    api = FakeAPI()
    bot = _bot(tmp_path, api=api, schedule_runner=schedule_runner)
    bot.process_update(_message("/schedule daily 08:15"))
    config = json.loads((tmp_path / "digest_config.json").read_text(encoding="utf-8"))
    assert config["delivery"] == {"frequency": "daily", "time": "08:15", "enabled": True}
    assert schedule_calls == [("daily", "08:15")]
    sent = [payload["text"] for method, payload, _ in api.calls if method == "sendMessage"]
    assert any("Розклад оновлено" in text for text in sent)


def test_invalid_schedule_does_not_mutate_config(tmp_path: Path):
    api = FakeAPI()
    bot = _bot(tmp_path, api=api, schedule_runner=lambda *_: (True, "ok"))
    bot.process_update(_message("/schedule yearly 28:90"))
    config = json.loads((tmp_path / "digest_config.json").read_text(encoding="utf-8"))
    assert config["delivery"] == {"frequency": "weekly", "time": "09:00"}
    assert any("Використання" in payload.get("text", "") for method, payload, _ in api.calls if method == "sendMessage")


def test_limit_queue_overlap_settings_are_bounded_and_persisted(tmp_path: Path):
    api = FakeAPI()
    bot = _bot(tmp_path, api=api)
    bot.process_update(_message("/limit 31"))
    bot.process_update(_message("/limit 12", update_id=2))
    bot.process_update(_message("/queue 0", update_id=3))
    bot.process_update(_message("/overlap off", update_id=4))
    config = json.loads((tmp_path / "digest_config.json").read_text(encoding="utf-8"))
    assert config["digest"]["limit"] == 12
    assert config["digest"]["queue_limit"] == 0
    assert config["digest"]["include_overlap"] is False


def test_topics_can_be_added_and_removed_with_bounds(tmp_path: Path):
    api = FakeAPI()
    bot = _bot(tmp_path, api=api)
    bot.process_update(_message("/topic add irony | context-aware irony detection"))
    config_path = tmp_path / "digest_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert len(config["queries"]) == 2
    assert config["queries"][1]["name"] == "irony"
    assert config["queries"][1]["per_source"] == 5
    assert config["queries"][1]["sources"] == ["openalex"]
    bot.process_update(_message("/topic remove irony", update_id=2))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert len(config["queries"]) == 1


def test_bot_ignores_commands_from_an_unconfigured_chat(tmp_path: Path):
    api = FakeAPI()
    bot = _bot(tmp_path, api=api)
    bot.process_update(_message("/help", chat_id=99999))
    assert not [call for call in api.calls if call[0] == "sendMessage"]


def test_poller_persists_offset_and_sends_menu_response(tmp_path: Path):
    api = FakeAPI(updates=[_message("/start", update_id=24)])
    bot = _bot(tmp_path, api=api)
    assert bot.poll_once(timeout=2) == 1
    state = json.loads((tmp_path / "data" / "telegram_bot_state.json").read_text(encoding="utf-8"))
    assert state["next_update_offset"] == 25
    messages = [payload for method, payload, _ in api.calls if method == "sendMessage"]
    assert messages and "LitRadar" in messages[0]["text"]
    assert "reply_markup" in messages[0]


def test_commands_are_available_in_telegram_menu(tmp_path: Path):
    api = FakeAPI()
    bot = _bot(tmp_path, api=api)
    bot._set_commands()
    method, payload, _ = api.calls[0]
    assert method == "setMyCommands"
    assert {item["command"] for item in payload["commands"]} >= {"digest", "schedule", "topic", "search", "jobs"}
