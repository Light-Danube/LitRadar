"""Real Textual Pilot keyboard behavior; synthetic data and mocked OS actions."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.skipif(
    importlib.util.find_spec("textual") is None, reason="Textual UI dependency is optional")]


@pytest.fixture
def synthetic_app(tmp_path, monkeypatch):
    import ui
    from config import RadarConfig
    from sources.base import Paper

    profile, config = tmp_path / "profile.json", tmp_path / "jobs.json"
    profile.write_text(json.dumps({"name": "Synthetic", "groups": [],
                                  "ranking": {"keyword_weight": 1, "semantic_weight": 0}}), encoding="utf-8")
    config.write_text('{"scan":{"enabled":false},"delivery":{"enabled":false}}', encoding="utf-8")
    # Patch before construction: do not create/read checkout defaults or .env.
    monkeypatch.setattr(ui, "ensure_user_defaults", lambda: None)
    monkeypatch.setattr(ui, "DEFAULT_PROFILE", profile)
    monkeypatch.setattr(ui, "DEFAULT_SCAN_CONFIG", config)
    monkeypatch.setitem(ui.ScheduleScreen.__init__.__kwdefaults__, "profile_path", profile)
    monkeypatch.setattr(RadarConfig, "load", classmethod(lambda cls: RadarConfig()))
    monkeypatch.setattr(ui, "is_available_offline", lambda row: False)
    searches = []
    monkeypatch.setattr(ui, "search_and_ingest", lambda *a, **kw: searches.append(a))
    def build(language):
        app = ui.LitRadarApp(tmp_path / f"library-{language}.sqlite3", language=language)
        paper = app.store.upsert_paper(Paper(source="fixture", title="Synthetic keyboard paper"),
                                       relevance_score=.8, matched_groups={})
        app.store.set_tags(paper, ["review"])
        return app, paper, searches, config, profile
    return build


@pytest.mark.parametrize("language", ["en", "uk"])
async def test_help_scroll_keyboard_close_and_modal_shortcuts(language, synthetic_app):
    from textual.containers import VerticalScroll
    from textual.widgets import Button, DataTable, Input, Static
    from ui import HelpScreen
    from ui_locales import HELP_TEXT, tr

    app, paper, searches, _, _ = synthetic_app(language)
    async with app.run_test(size=(80, 24)) as pilot:
        app.query_one("#source_query", Input).value = "Unsaved query Україна"
        app.query_one("#papers", DataTable).focus()
        await pilot.press("?")
        assert isinstance(app.screen, HelpScreen)
        assert str(app.screen.query_one("#help_body", Static).renderable) == tr(language, HELP_TEXT)
        assert str(app.screen.query_one("#help_close", Button).label) == tr(language, "Close")
        assert app.focused.id == "help_scroll"
        await pilot.press("end")
        await pilot.pause()
        assert app.screen.query_one("#help_scroll", VerticalScroll).scroll_y > 0
        await pilot.press("r", "d", "y", "ctrl+enter")
        assert app.store.get(paper)["status"] == "new"
        assert not app.store.feedback_rows() and not searches
        await pilot.press("tab")
        assert app.focused.id == "help_close"
        await pilot.press("enter")
        assert not isinstance(app.screen, HelpScreen)
        assert app.focused.id == "papers"
        assert app.query_one("#source_query", Input).value == "Unsaved query Україна"
        await pilot.press("?", "escape")
        assert app.focused.id == "papers"


@pytest.mark.parametrize("language", ["en", "uk"])
async def test_tags_unicode_save_cancel_preserve_filters_and_query(language, synthetic_app):
    from textual.widgets import Button, DataTable, Input, Select, Static
    from ui import TagScreen
    from ui_locales import tr

    app, paper, searches, _, _ = synthetic_app(language)
    async with app.run_test(size=(80, 24)) as pilot:
        app.query_one("#search", Input).value = "Synthetic"
        app.query_one("#source_query", Input).value = "Unsaved source draft Україна"
        app.query_one("#tag", Select).value = "review"
        app.query_one("#sort", Select).value = "title"
        await pilot.pause()
        app.query_one("#papers", DataTable).focus()
        await pilot.press("g")
        assert isinstance(app.screen, TagScreen) and app.focused.id == "tag_input"
        assert str(app.screen.query_one("#tag_title", Static).renderable) == tr(language, "[b]Edit tags[/b]")
        assert str(app.screen.query_one("#tag_save", Button).label) == tr(language, "Save")
        assert str(app.screen.query_one("#tag_cancel", Button).label) == tr(language, "Cancel")
        await pilot.press("end", ",", "space", *list("доказ"), "tab")
        assert app.focused.id == "tag_save"
        await pilot.press("enter")
        assert not isinstance(app.screen, TagScreen)
        assert app.focused.id == "papers"
        assert json.loads(app.store.get(paper)["tags_json"]) == ["review", "доказ"]
        await pilot.press("g", "end", ",", "space", *list("відкинути"), "tab", "tab")
        assert app.focused.id == "tag_cancel"
        await pilot.press("enter")
        assert app.focused.id == "papers"
        assert json.loads(app.store.get(paper)["tags_json"]) == ["review", "доказ"]
        assert app.store.get(paper)["status"] == "new" and not searches
        assert app.query_one("#search", Input).value == "Synthetic"
        assert app.query_one("#source_query", Input).value == "Unsaved source draft Україна"
        assert app.query_one("#tag", Select).value == "review"
        assert app.query_one("#sort", Select).value == "title"


@pytest.mark.parametrize("language", ["en", "uk"])
async def test_tag_write_failure_keeps_draft_rolls_back_and_allows_retry_or_cancel(language, synthetic_app, monkeypatch):
    from textual.widgets import Button, DataTable, Input, Static
    from ui import TagScreen
    from ui_locales import tr

    app, paper, _, _, _ = synthetic_app(language)
    original = app.store.set_tags
    attempts = []
    def fail_after_write(paper_id, tags):
        attempts.append(list(tags))
        if len(attempts) in {1, 3}:
            app.store.conn.execute("UPDATE papers SET tags_json=? WHERE id=?",
                                   (json.dumps(["uncommitted-corruption"]), paper_id))
            raise sqlite3.OperationalError("SYNTHETIC_PRIVATE_DISK_ERROR_DO_NOT_ECHO")
        return original(paper_id, tags)
    monkeypatch.setattr(app.store, "set_tags", fail_after_write)
    async with app.run_test(size=(80, 24)) as pilot:
        app.query_one("#papers", DataTable).focus()
        await pilot.press("g", "end", ",", "space", *list("доказ"), "enter")
        assert app.is_running and isinstance(app.screen, TagScreen)
        assert app.focused.id == "tag_input"
        assert app.screen.query_one("#tag_input", Input).value == "review, доказ"
        assert not app.store.conn.in_transaction
        assert json.loads(app.store.get(paper)["tags_json"]) == ["review"]
        message = str(app.screen.query_one("#tag_error", Static).renderable)
        assert message == tr(language, "Could not save tags. Your draft is retained; retry or cancel.")
        assert "SYNTHETIC_PRIVATE" not in message and "OperationalError" not in message
        await pilot.pause()
        assert str(app.screen.query_one("#tag_error", Static).renderable) == message
        await pilot.press("tab")
        assert app.focused.id == "tag_save"
        await pilot.press("enter")
        assert not isinstance(app.screen, TagScreen) and app.focused.id == "papers"
        assert json.loads(app.store.get(paper)["tags_json"]) == ["review", "доказ"]
        await pilot.press("g", "end", ",", "space", *list("відкинути"), "tab")
        assert str(app.screen.query_one("#tag_save", Button).label) == tr(language, "Save")
        await pilot.press("enter")
        assert isinstance(app.screen, TagScreen) and app.focused.id == "tag_input"
        assert app.screen.query_one("#tag_input", Input).value.endswith(", відкинути")
        assert not app.store.conn.in_transaction
        assert json.loads(app.store.get(paper)["tags_json"]) == ["review", "доказ"]
        await pilot.press("escape")
        assert app.focused.id == "papers"
        assert json.loads(app.store.get(paper)["tags_json"]) == ["review", "доказ"]
        assert len(attempts) == 3


@pytest.mark.parametrize("language", ["en", "uk"])
async def test_jobs_localized_failures_persist_and_keyboard_controls_recover(language, synthetic_app, monkeypatch):
    import ui
    from textual.containers import VerticalScroll
    from textual.widgets import Button, DataTable, Static
    from ui_locales import tr

    calls = []
    long_error = "\n".join(f"Synthetic scheduler failure line {number}" for number in range(50))
    assert len(long_error.splitlines()) == 50
    def scheduler(command, **kwargs):
        calls.append(command)
        if len(calls) == 1:
            raise OSError("Synthetic scheduler unavailable")
        return subprocess.CompletedProcess(command, 7, "", long_error)
    monkeypatch.setattr(ui.subprocess, "run", scheduler)
    app, paper, _, config, profile = synthetic_app(language)
    async with app.run_test(size=(80, 24)) as pilot:
        app.query_one("#papers", DataTable).focus()
        await pilot.press("j")
        assert isinstance(app.screen, ui.ScheduleScreen)
        screen = app.screen
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert str(screen.query_one("#schedule_title", Static).renderable) == tr(language, "Scheduled jobs")
        assert str(screen.query_one("#schedule_status_btn", Button).label) == tr(language, "Refresh status")
        expected = tr(language, "Could not run scheduler command: {error}: {message}",
                      error="OSError", message="Synthetic scheduler unavailable")
        assert str(screen.query_one("#schedule_status", Static).renderable) == expected
        assert all(not button.disabled for button in screen.query(Button))
        screen.query_one("#schedule_status_btn", Button).focus()
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        expected = tr(language, "Command exit code {code}.\n{message}", code=7, message=long_error)
        assert str(screen.query_one("#schedule_status", Static).renderable) == expected
        assert all(not button.disabled for button in screen.query(Button))
        await pilot.pause()
        assert str(screen.query_one("#schedule_status", Static).renderable) == expected
        assert screen.query_one("#schedule_status_scroll", VerticalScroll).can_focus
        # Running the command disables Refresh and can move its focus. Start
        # from a known control; require actual keyboard reachability, not order.
        screen.query_one("#schedule_close", Button).focus()
        visited = []
        for _ in range(12):
            await pilot.press("tab")
            visited.append(app.focused.id)
            if app.focused.id == "schedule_status_scroll":
                break
        assert "schedule_status_scroll" in visited, visited
        await pilot.press("end")
        await pilot.pause()
        status = screen.query_one("#schedule_status_scroll", VerticalScroll)
        assert status.max_scroll_y >= 40
        assert status.scroll_y == status.max_scroll_y
        await pilot.press("home")
        await pilot.pause()
        assert screen.query_one("#schedule_status_scroll", VerticalScroll).scroll_y == 0
        assert len(calls) == 2
        assert all(command[command.index("schedule") + 1] == "status" for command in calls)
        assert all(command[command.index("--config") + 1] == str(config) for command in calls)
        assert all(command[command.index("--profile") + 1] == str(profile) for command in calls)
        assert app.store.get(paper)["status"] == "new"
        await pilot.press("escape")
        assert not isinstance(app.screen, ui.ScheduleScreen) and app.focused.id == "papers"
