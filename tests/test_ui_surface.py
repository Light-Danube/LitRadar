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
        assert app.query_one("#main")
        assert app.query_one("#papers")
        assert app.query_one("#details")

        bindings = {binding.key for binding in app.BINDINGS}
        assert {"?", "g", "k", "l", "s", "y", "n", "i", "ctrl+enter"}.issubset(bindings)


@pytest.mark.skipif(importlib.util.find_spec("textual") is None, reason="Textual UI dependency is optional")
def test_search_highlighting_is_confined_to_abstract_and_keeps_plain_text():
    from ui import highlight_search_terms

    body = "Title: context attribution\nAbstract: Context attribution matters. The [word] stays literal."
    abstract = "Context attribution matters. The [word] stays literal."
    rendered = highlight_search_terms(body, abstract, "context attribution")
    assert rendered.plain == body
    highlighted = [
        span for span in rendered.spans
        if span.style and span.style.bold and span.style.color and span.style.color.name == "yellow"
    ]
    assert len(highlighted) == 2
    # The occurrence in the title is intentionally not highlighted.
    assert all(span.start >= body.index("Abstract:") for span in highlighted)
