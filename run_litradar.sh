#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
VENV="$PWD/.venv"
PY="$VENV/bin/python"
MARKER="$VENV/.litradar-deps-0.6.0"
if [[ ! -x "$PY" ]]; then
  python3 -m venv "$VENV"
fi
if [[ ! -f "$MARKER" ]]; then
  "$PY" -m pip install --upgrade pip
  "$PY" -m pip install -r requirements.txt -r requirements-ui.txt
  touch "$MARKER"
fi
if [[ $# -eq 0 ]]; then
  exec "$PY" cli.py ui
else
  exec "$PY" cli.py "$@"
fi
