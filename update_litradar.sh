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
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt -r requirements-ui.txt -r requirements-dev.txt -r requirements-llm.txt -r requirements-web.txt
rm -f "$VENV"/.litradar-deps-*
touch "$VENV/.litbeacon-deps-0.8.0-full"
"$PYTHON" cli.py init
"$PYTHON" -m pytest -q
echo 'LitBeacon update verified.'
