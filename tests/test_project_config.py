from __future__ import annotations

from pathlib import Path


def test_pyproject_configures_repository_pythonpath():
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'pythonpath = ["."]' in text
    assert 'testpaths = ["tests"]' in text


def test_packaging_metadata_includes_runtime_modules_and_optional_web_ui():
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.8.0"' in text
    assert '"workspace_web"' in text
    assert 'web = ["fastapi>=0.115,<1", "uvicorn>=0.30,<1"]' in text
    assert 'web = ["index.html", "static/*.js", "static/*.css"]' in text
    assert '"pipeline", "notes", "citation_intelligence", "research_digest", "telegram_bot"' in text
    workflow = (root / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "-r requirements-ui.txt" in workflow
