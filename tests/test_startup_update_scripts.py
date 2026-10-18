from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cross_platform_launchers_and_updaters_exist():
    for name in ("setup_litbeacon.bat", "run_litbeacon.bat", "run_litbeacon_cli.bat", "run_litbeacon_telegram.bat", "run_litbeacon_web.bat", "run_litbeacon.ps1", "run_litbeacon.sh", "update_litbeacon.bat", "update_litbeacon.ps1", "update_litbeacon.sh", "schedule_litbeacon.ps1", "install_litbeacon_schedule.bat"):
        path = ROOT / name
        assert path.exists(), name
        assert path.stat().st_size > 50
    assert ".venv" in (ROOT / "run_litbeacon.bat").read_text(encoding="utf-8")
    updater = (ROOT / "update_litbeacon.ps1").read_text(encoding="utf-8")
    assert "--ff-only" in updater
    assert "no .git directory" in updater
    batch_updater = (ROOT / "update_litbeacon.bat").read_text(encoding="utf-8").lower()
    assert "pause >nul" in batch_updater
    assert "update_exit_code" in batch_updater


def test_release_workflow_attaches_verified_runtime_package_after_publication():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "release:" in workflow
    assert "types: [published]" in workflow
    assert "pip wheel --no-deps" in workflow
    assert 'scripts.build_user_bundle' in workflow and '--tag "$RELEASE_TAG"' in workflow
    assert 'built_wheel_smoke.py' in workflow
    assert "softprops/action-gh-release" in workflow
    assert "dist/*.whl" in workflow and "dist/*-setup.zip" in workflow


def test_windows_launcher_checks_errors_inside_parenthesized_blocks_safely():
    root = Path(__file__).resolve().parents[1]
    text = (root / "run_litbeacon.bat").read_text(encoding="utf-8")
    # The shared setup helper prevents fragile pip commands inside compound blocks.
    assert 'call "%~dp0setup_litbeacon.bat"' in text
    assert "if errorlevel 1 goto failed" in text
    assert "if errorlevel 1 exit /b %errorlevel%" not in text


def test_normal_launchers_install_only_application_extras_and_keep_legacy_aliases():
    root = Path(__file__).resolve().parents[1]
    for name in ("setup_litbeacon.bat", "run_litbeacon.ps1", "update_litbeacon.ps1", "run_litbeacon.sh", "update_litbeacon.sh"):
        text = (root / name).read_text(encoding="utf-8")
        assert ".[web,ui]" in text or "setup_litbeacon.bat" in text or ".[web,ui,annotations]" in text
        assert "requirements-dev.txt" not in text and "requirements-semantic.txt" not in text
    setup = (root / "setup_litbeacon.bat").read_text(encoding="utf-8")
    assert ".[web,ui,annotations]" not in setup
    assert ".[web,ui,annotations]" not in (root / "update_litbeacon.ps1").read_text(encoding="utf-8")
    assert "py -3.12" in setup and ".venv-before-python312" in setup and "pause >nul" in setup
    assert 'move "%VENV%" "%BACKUP%"' in setup
    for old, new in (("setup_litradar.bat", "setup_litbeacon.bat"), ("run_web.bat", "run_litbeacon_web.bat"), ("run_litradar.bat", "run_litbeacon.bat")):
        assert new in (root / old).read_text(encoding="utf-8")
    cli = (root / "run_litbeacon_cli.bat").read_text(encoding="utf-8")
    assert "cmd /k" in cli
    bot = (root / "run_litbeacon_telegram.bat").read_text(encoding="utf-8")
    assert "telegram-run" in bot
    web = (root / "run_litbeacon_web.bat").read_text(encoding="utf-8")
    assert 'call "%~dp0setup_litbeacon.bat"' in web
    assert "cli.py web" in web


def test_schedule_installer_uses_task_scheduler_and_safe_user_context():
    root = Path(__file__).resolve().parents[1]
    script = (root / "schedule_litradar.ps1").read_text(encoding="utf-8")
    assert "Register-ScheduledTask" in script
    assert "-StartWhenAvailable" in script
    assert "-MultipleInstances IgnoreNew" in script
    assert "LitRadar-Scan" in script and "LitRadar-Digest" in script
    assert "-LogonType Interactive" in script
    batch = (root / "install_litbeacon_schedule.bat").read_text(encoding="utf-8")
    assert "--job scan --frequency daily" in batch
    assert "--job digest --frequency weekly" in batch


def test_zip_updater_refreshes_dependencies_but_does_not_claim_code_was_updated():
    root = Path(__file__).resolve().parents[1]
    text = (root / "update_litbeacon.bat").read_text(encoding="utf-8")
    assert 'if not exist "%~dp0.git" goto zip_install' in text
    assert 'call "%~dp0setup_litbeacon.bat"' in text
    assert "source files were NOT updated" in text
    assert "update_exit_code" in text.lower()
