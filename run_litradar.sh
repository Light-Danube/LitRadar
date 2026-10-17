#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
VENV="$PWD/.venv"
PYTHON="$VENV/bin/python"
MARKER="$VENV/.litbeacon-deps-1.0.0-full"
if [[ ! -x "$PYTHON" ]]; then python3 -m venv "$VENV"; fi
if [[ ! -f "$MARKER" ]]; then
  "$PYTHON" -m pip install --upgrade pip
  "$PYTHON" -m pip install -r requirements.txt -r requirements-ui.txt -r requirements-dev.txt -r requirements-llm.txt -r requirements-web.txt
  touch "$MARKER"
fi
"$PYTHON" cli.py init
if [[ $# -eq 0 ]]; then "$PYTHON" cli.py ui; else "$PYTHON" cli.py "$@"; fi
