"""Locations for immutable application assets and writable local user data."""
from __future__ import annotations

import os
import sys
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
ASSET_ROOT = Path(__file__).resolve().parent / "assets"
SOURCE_CHECKOUT = (CODE_ROOT / "pyproject.toml").is_file() and (CODE_ROOT / "VERSION").is_file()


def _user_root() -> Path:
    override = os.environ.get("LITBEACON_HOME") or os.environ.get("LITRADAR_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if SOURCE_CHECKOUT:
        return CODE_ROOT
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "LitBeacon"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "LitBeacon"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "LitBeacon"


WORKSPACE_ROOT = _user_root()
DATA_ROOT = WORKSPACE_ROOT / "data"
DEFAULT_DB = DATA_ROOT / "litradar.sqlite3"
DEFAULT_PROFILE = WORKSPACE_ROOT / "research_profile.json"
DEFAULT_SCAN_CONFIG = WORKSPACE_ROOT / "digest_config.json"
VERSION = ((CODE_ROOT if SOURCE_CHECKOUT else ASSET_ROOT) / "VERSION").read_text(encoding="utf-8").strip()


def ensure_user_defaults() -> None:
    """Seed missing editable defaults on explicit startup, never replace user edits."""
    if WORKSPACE_ROOT == CODE_ROOT and SOURCE_CHECKOUT:
        return
    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)
    for name in ("research_profile.json", "digest_config.json"):
        content = ((CODE_ROOT if SOURCE_CHECKOUT else ASSET_ROOT) / name).read_bytes()
        try:
            with (WORKSPACE_ROOT / name).open("xb") as handle:
                handle.write(content)
        except FileExistsError:
            pass
