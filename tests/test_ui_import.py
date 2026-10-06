from __future__ import annotations

import importlib.util

import pytest


def test_ui_module_imports_when_textual_available():
    if importlib.util.find_spec("textual") is None:
        pytest.skip("Textual UI dependency is optional")
    import ui  # noqa: F401
