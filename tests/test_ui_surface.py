from __future__ import annotations

import importlib.util

import pytest


@pytest.mark.skipif(importlib.util.find_spec("textual") is None, reason="Textual UI dependency is optional")
def test_ui_composes_expected_controls(tmp_path):
    from ui import LitRadarApp

    app = LitRadarApp(tmp_path / "library.sqlite3")
    children = list(app.compose())
    assert len(children) == 4
    bindings = {binding.key for binding in app.BINDINGS}
    assert {"?", "g", "l", "s"}.issubset(bindings)
    app.store.close()
