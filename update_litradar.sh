#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ ! -d .git ]]; then
  echo 'This folder is not a Git checkout. Clone/publish the repository first.' >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'Update stopped: commit/stash tracked changes in GitHub Desktop first.' >&2
  exit 3
fi
git pull --ff-only
VENV="$PWD/.venv"
PY="$VENV/bin/python"
if [[ ! -x "$PY" ]]; then
  python3 -m venv "$VENV"
fi
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r requirements.txt -r requirements-ui.txt -r requirements-dev.txt
"$PY" cli.py init
"$PY" -m pytest -q
