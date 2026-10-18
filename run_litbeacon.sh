#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
VENV="$PWD/.venv"
PYTHON="$VENV/bin/python"
MARKER="$VENV/.litbeacon-deps-1.0.0-local"
if [[ ! -x "$PYTHON" ]]; then python3 -m venv "$VENV"; fi
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 11), "LitBeacon needs Python 3.11+"'
if [[ ! -f "$MARKER" ]]; then
  "$PYTHON" -m pip install '.[web,ui,annotations]'
  "$PYTHON" -m pip check
  touch "$MARKER"
fi
"$PYTHON" cli.py init
if [[ $# -eq 0 ]]; then "$PYTHON" cli.py ui; else "$PYTHON" cli.py "$@"; fi
