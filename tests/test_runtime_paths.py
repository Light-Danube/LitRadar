"""Default path contracts without opening any personal library/configuration."""
import os
from pathlib import Path
import subprocess
import sys


def _run(code, **environment):
    return subprocess.run([sys.executable, "-c", code], env={**os.environ, **environment},
                          check=True, capture_output=True, text=True).stdout.strip()


def test_source_checkout_keeps_legacy_defaults():
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    for name in ("LITBEACON_HOME", "LITRADAR_HOME"):
        env.pop(name, None)
    result = subprocess.run([sys.executable, "-c", "from litradar_runtime import DEFAULT_DB; print(DEFAULT_DB)"],
                            env=env, check=True, capture_output=True, text=True)
    assert Path(result.stdout.strip()) == root / "data" / "litradar.sqlite3"


def test_explicit_home_seeds_defaults_without_overwriting(tmp_path):
    code = """
from litradar_runtime import ensure_user_defaults, DEFAULT_SCAN_CONFIG, DEFAULT_DB
ensure_user_defaults()
assert DEFAULT_SCAN_CONFIG.is_file()
DEFAULT_SCAN_CONFIG.write_text('edited', encoding='utf-8')
ensure_user_defaults()
assert DEFAULT_SCAN_CONFIG.read_text(encoding='utf-8') == 'edited'
print(DEFAULT_DB)
"""
    assert Path(_run(code, LITBEACON_HOME=str(tmp_path), LITRADAR_HOME=str(tmp_path / "legacy"))) == tmp_path / "data" / "litradar.sqlite3"


def test_legacy_home_override(tmp_path):
    assert Path(_run("from litradar_runtime import WORKSPACE_ROOT; print(WORKSPACE_ROOT)",
                     LITBEACON_HOME="", LITRADAR_HOME=str(tmp_path))) == tmp_path


def test_import_does_not_create_user_home(tmp_path):
    destination = tmp_path / "uncreated"
    _run("import cli, config, offline, research_digest, telegram_bot", LITBEACON_HOME=str(destination))
    assert not destination.exists()


def test_installed_platform_defaults_stay_outside_package(tmp_path):
    import shutil
    package = tmp_path / "installed" / "litradar_runtime"
    package.mkdir(parents=True)
    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(root / "litradar_runtime" / "__init__.py", package / "__init__.py")
    assets = package / "assets"
    assets.mkdir()
    (assets / "VERSION").write_text("0.8.0", encoding="utf-8")
    for platform, expected in (
        ("linux", tmp_path / "xdg" / "LitBeacon"),
        ("win32", tmp_path / "local-appdata" / "LitBeacon"),
        ("darwin", tmp_path / "home" / "Library" / "Application Support" / "LitBeacon"),
    ):
        code = f"""
import sys
from pathlib import Path
sys.path.insert(0, {str(package.parent)!r})
sys.platform = {platform!r}
Path.home = classmethod(lambda cls: Path({str(tmp_path / 'home')!r}))
from litradar_runtime import WORKSPACE_ROOT, SOURCE_CHECKOUT
assert not SOURCE_CHECKOUT
print(WORKSPACE_ROOT)
"""
        assert Path(_run(code, LITBEACON_HOME="", LITRADAR_HOME="", XDG_DATA_HOME=str(tmp_path / "xdg"),
                         LOCALAPPDATA=str(tmp_path / "local-appdata"))) == expected
