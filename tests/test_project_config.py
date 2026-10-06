from __future__ import annotations

from pathlib import Path


def test_pyproject_configures_repository_pythonpath():
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'pythonpath = ["."]' in text
    assert 'testpaths = ["tests"]' in text
