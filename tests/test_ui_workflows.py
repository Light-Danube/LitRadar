"""Real Textual event-loop regressions; all data and external operations are synthetic."""
from __future__ import annotations

import importlib.util
import subprocess
import asyncio
import threading
from types import SimpleNamespace

import pytest

pytestmark = [
    pytest.mark.skipif(importlib.util.find_spec("textual") is None, reason="Textual UI dependency is optional"),
    pytest.mark.asyncio,
]


def synthetic_app(tmp_path):
    from sources.base import Paper
    from ui import LitRadarApp

    app = LitRadarApp(tmp_path / "library.sqlite3")
    ids = []
    for title, abstract, year, score in [
        ("Zulu synthetic", "context attribution [literal]", "2020-01-01", 0.9),
        ("Alpha synthetic", "another synthetic abstract", "2024-01-01", 0.2),
    ]:
        ids.append(app.store.upsert_paper(Paper(source="synthetic", title=title,
            abstract=abstract, published_at=year, doi=f"10.0000/synthetic-{year}"),
            relevance_score=score, matched_groups={}))
    return app, ids


async def test_keyboard_status_feedback_and_restore(tmp_path):
    from textual.widgets import DataTable

    app, ids = synthetic_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        app.query_one("#papers", DataTable).focus()
        for key, expected in [("t", "to-read"), ("r", "read"), ("d", "dismissed"), ("u", "new")]:
            await pilot.press(key)
            assert app.store.get(ids[0])["status"] == expected
        await pilot.press("y", "n")
        assert app.store.feedback_rows()


async def test_filters_sort_empty_selection_and_safe_details(tmp_path):
    from textual.widgets import Input, Select, Static

    app, ids = synthetic_app(tmp_path)
    app.store.set_tags(ids[0], ["review"])
    app.store.set_status(ids[1], "read")
    async with app.run_test(size=(120, 40)) as pilot:
        app.query_one("#sort", Select).value = "title"
        await pilot.pause()
        assert [row["id"] for row in app.current_rows] == [ids[1], ids[0]]
        app.query_one("#status", Select).value = "read"
        await pilot.pause()
        assert [row["id"] for row in app.current_rows] == [ids[1]]
        app.query_one("#status", Select).value = "all"
        app.query_one("#tag", Select).value = "review"
        await pilot.pause()
        assert [row["id"] for row in app.current_rows] == [ids[0]]
        assert "[literal]" in app.query_one("#details_body", Static).renderable.plain
        app.query_one("#search", Input).value = "no matching synthetic title"
        await pilot.pause()
        assert not app.current_rows
        assert app._selected_id() is None
        app.action_mark_read()
        assert app.store.get(ids[0])["status"] == "new"


async def test_tag_editor_typing_save_cancel_and_focus(tmp_path):
    from textual.widgets import DataTable, Input, Select
    from ui import TagScreen

    app, ids = synthetic_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        app.query_one("#papers", DataTable).focus()
        await pilot.press("g")
        assert isinstance(app.screen, TagScreen)
        assert app.focused.id == "tag_input"
        await pilot.press("r", "d", "q", "j", "enter")
        assert not isinstance(app.screen, TagScreen)
        assert app.store.get(ids[0])["status"] == "new"
        assert app.store.all_tags() == ["rdqj"]
        app.query_one("#tag", Select).value = "rdqj"
        await pilot.pause()
        assert app.query_one("#tag", Select).value == "rdqj"
        assert [row["id"] for row in app.current_rows] == [ids[0]]
        app.query_one("#papers", DataTable).focus()
        await pilot.press("g")
        app.screen.query_one("#tag_input", Input).value = "discard me"
        await pilot.press("escape")
        assert app.store.all_tags() == ["rdqj"]


async def test_help_modal_does_not_mutate_library(tmp_path):
    from textual.widgets import DataTable
    from ui import HelpScreen

    app, ids = synthetic_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        app.query_one("#papers", DataTable).focus()
        await pilot.press("?")
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("r", "d", "y")
        assert app.store.get(ids[0])["status"] == "new"
        assert not app.store.feedback_rows()
        await pilot.press("escape")
        assert not isinstance(app.screen, HelpScreen)


async def test_jobs_all_actions_use_thread_safe_ui_dispatch(tmp_path, monkeypatch):
    from textual.widgets import Button, Static
    from ui import ScheduleScreen

    calls = []
    def scheduler(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "Synthetic scheduler status", "")
    monkeypatch.setattr("ui.subprocess.run", scheduler)
    app, _ = synthetic_app(tmp_path)
    async with app.run_test(size=(140, 50)) as pilot:
        screen = ScheduleScreen(tmp_path / "synthetic-config.json")
        app.push_screen(screen)
        await pilot.pause()
        await app.workers.wait_for_complete()
        assert "Synthetic scheduler" in str(screen.query_one("#schedule_status", Static).renderable)
        for control, action, job in [
            ("schedule_status_btn", "status", "all"),
            ("schedule_install_scan", "install", "scan"),
            ("schedule_install_digest", "install", "digest"),
            ("schedule_remove_scan", "remove", "scan"),
            ("schedule_remove_digest", "remove", "digest"),
            ("schedule_remove_all", "remove", "all"),
        ]:
            screen.query_one(f"#{control}", Button).focus()
            await pilot.press("enter")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert calls[-1][3] == action
            assert calls[-1][calls[-1].index("--job") + 1] == job
        await pilot.press("escape")
        assert not isinstance(app.screen, ScheduleScreen)


async def test_source_worker_success_and_failure_reenable_fetch(tmp_path, monkeypatch):
    from textual.widgets import Button, Input, ProgressBar, Static

    def search(query, **kwargs):
        kwargs["progress"]("completed", "synthetic", "two papers")
        return SimpleNamespace(fetched=2, newly_stored=0, library_total=2, source_errors={}), []
    monkeypatch.setattr("ui.search_and_ingest", search)
    app, _ = synthetic_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        app.query_one("#source_query", Input).value = "synthetic query"
        await pilot.pause()
        app.action_search_sources()
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert not app.query_one("#search_sources", Button).disabled
        assert app.query_one("#search_progress", ProgressBar).progress == 100
        def fail(*args, **kwargs):
            raise RuntimeError("synthetic provider failure")
        monkeypatch.setattr("ui.search_and_ingest", fail)
        app.action_search_sources()
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert not app.query_one("#search_sources", Button).disabled
        assert "synthetic provider failure" in str(app.query_one("#search_status", Static).renderable)


async def test_citation_worker_failure_releases_busy_state(tmp_path, monkeypatch):
    from textual.widgets import Button, Static

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic citation failure")
    monkeypatch.setattr("ui.explore_citation_graph", fail)
    app, _ = synthetic_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        app.action_explore_citations()
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert not app._citation_busy
        assert not app.query_one("#search_sources", Button).disabled
        assert "synthetic citation failure" in str(app.query_one("#search_status", Static).renderable)


@pytest.mark.parametrize("result, expected", [
    (OSError("synthetic scheduler unavailable"), "OSError"),
    (subprocess.TimeoutExpired("synthetic", 60), "TimeoutExpired"),
    (subprocess.CompletedProcess([], 7, "", "synthetic failure"), "7"),
    (subprocess.CompletedProcess([], 0, "", ""), "0"),
])
async def test_jobs_errors_are_visible_and_controls_recover(tmp_path, monkeypatch, result, expected):
    from textual.widgets import Button, Static
    from ui import ScheduleScreen

    def scheduler(*args, **kwargs):
        if isinstance(result, Exception):
            raise result
        return result
    monkeypatch.setattr("ui.subprocess.run", scheduler)
    app, _ = synthetic_app(tmp_path)
    async with app.run_test(size=(100, 35)) as pilot:
        screen = ScheduleScreen(tmp_path / "synthetic-config.json")
        app.push_screen(screen)
        await pilot.pause()
        await app.workers.wait_for_complete()
        assert expected in str(screen.query_one("#schedule_status", Static).renderable)
        assert not screen.query_one("#schedule_install_scan", Button).disabled


async def test_jobs_close_during_worker_and_busy_guard(tmp_path, monkeypatch):
    from textual.widgets import Button
    from ui import ScheduleScreen

    started, release, finished = threading.Event(), threading.Event(), threading.Event()
    calls = []
    def scheduler(command, **kwargs):
        calls.append(command)
        started.set()
        release.wait(timeout=5)
        finished.set()
        return subprocess.CompletedProcess(command, 0, "late synthetic result", "")
    monkeypatch.setattr("ui.subprocess.run", scheduler)
    app, _ = synthetic_app(tmp_path)
    async with app.run_test(size=(80, 24)) as pilot:
        screen = ScheduleScreen(tmp_path / "synthetic-config.json")
        app.push_screen(screen)
        try:
            await pilot.pause()
            assert started.is_set()
            assert screen.query_one("#schedule_install_scan", Button).disabled
            screen._start_schedule("remove", "all")
            assert len(calls) == 1
            await pilot.press("escape")
            assert not isinstance(app.screen, ScheduleScreen)
        finally:
            release.set()
        for _ in range(20):
            if finished.is_set():
                break
            await asyncio.sleep(0.01)
        await pilot.pause()
        assert finished.is_set()
        assert app.is_running


async def test_modal_blocks_source_shortcut(tmp_path, monkeypatch):
    from textual.widgets import Input
    from ui import HelpScreen

    calls = []
    monkeypatch.setattr("ui.search_and_ingest", lambda *args, **kwargs: calls.append(args))
    app, _ = synthetic_app(tmp_path)
    async with app.run_test(size=(80, 24)) as pilot:
        app.query_one("#source_query", Input).value = "synthetic query"
        app.push_screen(HelpScreen())
        await pilot.pause()
        await pilot.press("ctrl+enter")
        await pilot.pause()
        assert not calls
        assert isinstance(app.screen, HelpScreen)


@pytest.mark.parametrize("size", [(80, 24), (120, 40)])
async def test_help_keyboard_scroll_close_and_focus_restore(tmp_path, size):
    from textual.containers import VerticalScroll
    from textual.widgets import DataTable
    from ui import HelpScreen

    app, _ = synthetic_app(tmp_path)
    async with app.run_test(size=size) as pilot:
        app.query_one("#papers", DataTable).focus()
        await pilot.press("?")
        assert isinstance(app.screen, HelpScreen)
        scroll = app.screen.query_one("#help_scroll", VerticalScroll)
        scroll.focus()
        await pilot.press("end")
        await pilot.pause()
        if size == (80, 24):
            assert scroll.scroll_y > 0
        await pilot.press("escape")
        assert app.focused.id == "papers"


@pytest.mark.parametrize("has_pdf", [True, False])
async def test_offline_worker_reports_pdf_or_metadata_result(tmp_path, monkeypatch, has_pdf):
    from textual.widgets import DataTable
    messages = []
    monkeypatch.setattr("ui.save_paper_offline", lambda *args, **kwargs: {"has_pdf": has_pdf})
    app, _ = synthetic_app(tmp_path)
    monkeypatch.setattr(app, "notify", lambda message, **kwargs: messages.append((message, kwargs)))
    async with app.run_test(size=(120, 40)) as pilot:
        app.query_one("#papers", DataTable).focus()
        await pilot.press("l")
        await app.workers.wait_for_complete()
        assert messages[-1][0].startswith("Offline copy ready" if has_pdf else "Metadata saved; PDF unavailable")
        assert messages[-1][1]["severity"] == ("information" if has_pdf else "warning")


async def test_offline_write_failure_does_not_crash_and_stays_reviewable(tmp_path, monkeypatch):
    from textual.widgets import DataTable, Static
    def fail(*args, **kwargs):
        raise OSError("synthetic disk full")
    monkeypatch.setattr("ui.save_paper_offline", fail)
    app, _ = synthetic_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        app.query_one("#papers", DataTable).focus()
        await pilot.press("l")
        await app.workers.wait_for_complete()
        assert "Offline save failed: synthetic disk full" in str(app.query_one("#search_status", Static).renderable)
        assert app.is_running


async def test_open_prefers_local_pdf_and_doi_keeps_raw_identifier(tmp_path, monkeypatch):
    from textual.widgets import DataTable
    opened = []
    monkeypatch.setattr("ui.webbrowser.open", opened.append)
    local_pdf = tmp_path / "synthetic.pdf"
    local_pdf.write_bytes(b"%PDF-1.4 synthetic")
    monkeypatch.setattr("ui.offline_pdf_path", lambda row: local_pdf)
    app, _ = synthetic_app(tmp_path)
    async with app.run_test(size=(120, 40)) as pilot:
        app.query_one("#papers", DataTable).focus()
        await pilot.press("o", "i")
        assert opened == [local_pdf.as_uri(), "https://doi.org/10.0000/synthetic-2020-01-01"]
