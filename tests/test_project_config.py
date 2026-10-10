from __future__ import annotations

from pathlib import Path


def test_pyproject_configures_repository_pythonpath():
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'pythonpath = ["."]' in text
    assert 'testpaths = ["tests"]' in text


def test_packaging_metadata_includes_runtime_modules_and_optional_ui():
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.7.0"' in text
    assert '"pipeline", "notes", "citation_intelligence", "research_digest"' in text
    workflow = (root / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "-r requirements-ui.txt" in workflow
