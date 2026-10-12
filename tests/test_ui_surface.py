from __future__ import annotations

import importlib.util

import pytest



@pytest.mark.skipif(importlib.util.find_spec("textual") is None, reason="Textual UI dependency is optional")
@pytest.mark.asyncio
async def test_ui_mounts_expected_controls(tmp_path):
    from ui import LitRadarApp

    app = LitRadarApp(tmp_path / "library.sqlite3")
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()

        # Exercise Textual's real compose/mount lifecycle rather than calling
        # compose() directly. Compose context is only active while Textual
        # mounts the app, so direct list(app.compose()) is not a valid UI test.
        assert app.query_one("#toolbar")
        assert app.query_one("#search")
        assert app.query_one("#status")
        assert app.query_one("#sort")
        assert app.query_one("#tag")
        assert app.query_one("#library_count")
        assert app.query_one("#source_query")
        assert app.query_one("#search_sources")
        assert app.query_one("#search_status")
        assert app.query_one("#search_progress")
        assert app.query_one("#search_progress_row")
        assert app.query_one("#main")
        assert app.query_one("#papers")
        assert app.query_one("#details")

        bindings = {binding.key for binding in app.BINDINGS}
        assert {"?", "g", "k", "l", "s", "y", "n", "i", "c", "j", "ctrl+enter"}.issubset(bindings)


@pytest.mark.skipif(importlib.util.find_spec("textual") is None, reason="Textual UI dependency is optional")
def test_search_highlighting_is_confined_to_abstract_and_keeps_plain_text():
    from rich.style import Style

    from ui import highlight_search_terms

    body = "Title: context attribution\nAbstract: Context attribution matters. The [word] stays literal."
    abstract = "Context attribution matters. The [word] stays literal."
    rendered = highlight_search_terms(body, abstract, "context attribution")
    assert rendered.plain == body
    # Rich exposes Span.style as either a Style object or a style-definition
    # string depending on the Rich version bundled with Textual.
    highlighted = []
    for span in rendered.spans:
        style = Style.parse(span.style) if isinstance(span.style, str) else span.style
        if style and style.bold and style.color and style.color.name == "yellow":
            highlighted.append(span)
    assert len(highlighted) == 2
    # The occurrence in the title is intentionally not highlighted.
    assert all(span.start >= body.index("Abstract:") for span in highlighted)


@pytest.mark.skipif(importlib.util.find_spec("textual") is None, reason="Textual UI dependency is optional")
@pytest.mark.asyncio
async def test_source_search_progress_is_persistent_in_main_ui(tmp_path):
    from textual.widgets import ProgressBar, Static
    from ui import LitRadarApp

    app = LitRadarApp(tmp_path / "library.sqlite3")
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app._begin_source_search("context attribution", 2)
        app._handle_search_progress("started", "openalex", "request started")
        app._handle_search_progress("completed", "openalex", "received 4 papers")

        status = app.query_one("#search_status", Static)
        assert "context attribution" in str(status.renderable)
        assert "openalex: done" in str(status.renderable)
        assert app.query_one("#search_progress", ProgressBar).progress == 35

        app._handle_search_progress("phase", "ranking", "Ranking 4 fetched paper(s)…")
        assert "Ranking 4 fetched" in str(status.renderable)
        assert app.query_one("#search_progress", ProgressBar).progress == 78
