"""Run with the wheel interpreter outside the checkout; only synthetic local data."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="litbeacon-wheel-") as temporary:
        # Windows runner temporary paths may use a short name or junction alias.
        root = Path(temporary).resolve()
        os.environ["LITBEACON_HOME"] = str(root / "user")
        # Set the disposable home before any application imports.
        import cli
        import config
        import offline
        import telegram_bot
        from sources import cache
        from fastapi.testclient import TestClient
        from litradar_runtime import CODE_ROOT, WORKSPACE_ROOT, DEFAULT_DB, DEFAULT_PROFILE, DEFAULT_SCAN_CONFIG, VERSION
        from workspace_web import create_app, STATIC_ROOT

        assert not (CODE_ROOT / "pyproject.toml").exists(), "Smoke must import the installed wheel, not the checkout"
        assert Path(cli.__file__).parent == CODE_ROOT
        expected_home = (root / "user").resolve()
        assert WORKSPACE_ROOT == expected_home, f"Actual workspace {WORKSPACE_ROOT!s}; expected {expected_home!s}; temporary {temporary!s}"
        assert cli.build_parser().parse_args(["web", "--no-open-browser"]).host == "127.0.0.1"
        assert cli.DEFAULT_DB == DEFAULT_DB
        assert config.ENV_PATH == WORKSPACE_ROOT / ".env"
        assert offline.DEFAULT_OFFLINE_DIR.is_relative_to(WORKSPACE_ROOT)
        assert telegram_bot.DEFAULT_STATE.is_relative_to(WORKSPACE_ROOT)
        assert cache.DEFAULT_CACHE_DIR.is_relative_to(WORKSPACE_ROOT)

        def run(*arguments: str) -> str:
            result = subprocess.run([sys.executable, "-m", "cli", *arguments], cwd=root,
                                    check=False, capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
            return result.stdout

        assert f"LitBeacon {VERSION}" in run("--version")
        assert "venue" in run("--help")
        run("init")
        assert DEFAULT_DB.is_file()
        assert json.loads(DEFAULT_PROFILE.read_text(encoding="utf-8"))["groups"]
        assert json.loads(DEFAULT_SCAN_CONFIG.read_text(encoding="utf-8"))["queries"]
        fixture = root / "fixture.json"
        fixture.write_text(json.dumps([{"source": "openalex", "external_id": "W123", "title": "Synthetic wheel paper", "abstract": "adaptive context", "authors": ["Test Researcher"]}]), encoding="utf-8")
        run("ingest-fixture", str(fixture), "--no-semantic")
        assert "Synthetic wheel paper" in run("list")
        with TestClient(create_app()) as client:
            assert client.get("/api/health").json()["ok"]
            assert "<html" in client.get("/").text.lower()
            assets = list(STATIC_ROOT.rglob("*"))
            assert any(path.suffix == ".png" for path in assets)
            for asset in assets:
                if asset.is_file():
                    response = client.get("/static/" + asset.relative_to(STATIC_ROOT).as_posix())
                    assert response.status_code == 200, asset
                    assert response.content == asset.read_bytes(), asset
            papers = client.get("/api/papers").json()["items"]
            paper_id = papers[0]["id"]
            assert client.patch(f"/api/papers/{paper_id}", json={"notes": "Synthetic note Україна", "tags": ["wheel"], "status": "to-read"}).status_code == 200
        # Reopening independently verifies durable storage, not just an API echo.
        with TestClient(create_app()) as client:
            paper = client.get(f"/api/papers/{paper_id}").json()
            assert paper["notes"] == "Synthetic note Україна"
            assert paper["tags"] == ["wheel"] and paper["status"] == "to-read"
        custom_db = root / "custom-library" / "custom.sqlite3"
        run("--db", str(custom_db), "init")
        with TestClient(create_app(custom_db)) as client:
            assert client.get("/api/health").json()["database"] == "custom.sqlite3"
            assert client.get("/api/papers").json()["items"] == []
            assert client.get("/static/app.js").status_code == 200
        DEFAULT_SCAN_CONFIG.write_text('{"queries": [], "scan": {"enabled": false}}', encoding="utf-8")
        run("init")
        assert json.loads(DEFAULT_SCAN_CONFIG.read_text(encoding="utf-8"))["queries"] == [], "Do not overwrite edited user defaults"
        assert not list(CODE_ROOT.glob("*.sqlite3"))
        print(f"Built wheel CLI/version/defaults/static assets/web/edit/restart smoke passed on {sys.platform}; version {VERSION}")


if __name__ == "__main__":
    main()
