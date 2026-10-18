#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo 'LitBeacon updater — Git checkout mode'
if [[ ! -d .git ]]; then
  echo 'No .git directory: ZIP installs must apply release patches manually.' >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'Local tracked/untracked changes detected. Commit or stash them before updating.' >&2
  exit 3
fi
git pull --ff-only
VENV="$PWD/.venv"
PYTHON="$VENV/bin/python"
if [[ ! -x "$PYTHON" ]]; then python3 -m venv "$VENV"; fi
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 11), "LitBeacon needs Python 3.11+"'
"$PYTHON" -m pip install '.[web,ui,annotations]'
"$PYTHON" -m pip check
rm -f "$VENV"/.litradar-deps-*
touch "$VENV/.litbeacon-deps-1.0.0-local"
"$PYTHON" cli.py init
echo 'LitBeacon checkout updated and runtime dependencies installed.'
