from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cross_platform_launchers_and_updaters_exist():
    for name in ("run_litradar.bat", "run_litradar.ps1", "run_litradar.sh", "update_litradar.bat", "update_litradar.ps1", "update_litradar.sh"):
        path = ROOT / name
        assert path.exists(), name
        assert path.stat().st_size > 50
    assert ".venv" in (ROOT / "run_litradar.bat").read_text(encoding="utf-8")
    updater = (ROOT / "update_litradar.ps1").read_text(encoding="utf-8")
    assert "--ff-only" in updater
    assert "no .git directory" in updater
    batch_updater = (ROOT / "update_litradar.bat").read_text(encoding="utf-8").lower()
    assert "pause >nul" in batch_updater
    assert "update_exit_code" in batch_updater


def test_release_workflow_attaches_a_clean_zip():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "release:" in workflow
    assert "git archive" in workflow
    assert "softprops/action-gh-release" in workflow


def test_windows_launcher_checks_errors_inside_parenthesized_blocks_safely():
    root = Path(__file__).resolve().parents[1]
    text = (root / "run_litradar.bat").read_text(encoding="utf-8")
    # %ERRORLEVEL% expands when a batch block is parsed, so use a fixed nonzero
    # code for failures detected inside parenthesized sections.
    assert "if errorlevel 1 exit /b 1" in text
    assert "if errorlevel 1 exit /b %errorlevel%" not in text
