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
        assert app.query_one("#main")
        assert app.query_one("#papers")
        assert app.query_one("#details")

        bindings = {binding.key for binding in app.BINDINGS}
        assert {"?", "g", "l", "s"}.issubset(bindings)
