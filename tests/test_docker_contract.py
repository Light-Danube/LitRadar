"""Offline safety and packaging checks for optional Docker support."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_compose_binds_browser_only_to_host_loopback():
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert '"127.0.0.1:8765:8765"' in compose
    assert 'profiles: ["bot"]' in compose
    assert "./data:/app/data" in compose
    assert "./reports:/app/reports" in compose


def test_image_never_copies_research_state_or_secrets():
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    for pattern in (".env", "data/", "reports/", "logs/", ".venv", "*.sqlite3"):
        assert pattern in ignore


def test_image_includes_only_required_workflow_contract_inputs():
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert ".github/*" in ignore
    assert ".github/workflows/*" in ignore
    assert {line for line in ignore if line.startswith("!.github/workflows/")} == {
        "!.github/workflows/", "!.github/workflows/tests.yml", "!.github/workflows/release.yml",
    }


def test_bootstrap_initializes_persistent_digest_config():
    boot = (ROOT / "docker" / "boot.sh").read_text(encoding="utf-8")
    assert 'cp /app/digest_config.json /app/data/digest_config.json' in boot
    assert 'exec python cli.py telegram-run --config /app/data/digest_config.json' in boot
    assert 'exec python cli.py scan --config /app/data/digest_config.json' in boot
    assert 'exec python -m uvicorn workspace_web:create_app --factory' in boot
