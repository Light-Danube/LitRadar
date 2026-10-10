from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cross_platform_launchers_and_updaters_exist():
    for name in ("setup_litradar.bat", "run_litradar.bat", "run_cli.bat", "run_telegram_bot.bat", "run_litradar.ps1", "run_litradar.sh", "update_litradar.bat", "update_litradar.ps1", "update_litradar.sh", "schedule_litradar.ps1", "install_schedule.bat"):
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
    # The shared setup helper prevents fragile pip commands inside compound blocks.
    assert 'call "%~dp0setup_litradar.bat"' in text
    assert "if errorlevel 1 goto failed" in text
    assert "if errorlevel 1 exit /b %errorlevel%" not in text


def test_windows_helpers_install_all_requirement_sets():
    root = Path(__file__).resolve().parents[1]
    for name in ("setup_litradar.bat", "run_litradar.ps1", "update_litradar.ps1", "run_litradar.sh", "update_litradar.sh"):
        text = (root / name).read_text(encoding="utf-8")
        for requirement in ("requirements.txt", "requirements-ui.txt", "requirements-dev.txt", "requirements-llm.txt"):
            assert requirement in text, (name, requirement)
    cli = (root / "run_cli.bat").read_text(encoding="utf-8")
    assert "cmd /k" in cli
    bot = (root / "run_telegram_bot.bat").read_text(encoding="utf-8")
    assert "telegram-run" in bot


def test_schedule_installer_uses_task_scheduler_and_safe_user_context():
    root = Path(__file__).resolve().parents[1]
    script = (root / "schedule_litradar.ps1").read_text(encoding="utf-8")
    assert "Register-ScheduledTask" in script
    assert "-StartWhenAvailable" in script
    assert "-MultipleInstances IgnoreNew" in script
    assert "LitRadar-Scan" in script and "LitRadar-Digest" in script
    assert "-LogonType Interactive" in script
    batch = (root / "install_schedule.bat").read_text(encoding="utf-8")
    assert "--job scan --frequency daily" in batch
    assert "--job digest --frequency weekly" in batch


def test_zip_updater_refreshes_dependencies_but_does_not_claim_code_was_updated():
    root = Path(__file__).resolve().parents[1]
    text = (root / "update_litradar.bat").read_text(encoding="utf-8")
    assert 'if not exist "%~dp0.git" goto zip_install' in text
    assert 'call "%~dp0setup_litradar.bat"' in text
    assert "source files were NOT updated" in text
    assert "update_exit_code" in text.lower()
