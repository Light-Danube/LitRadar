#!/bin/sh
set -eu

cd /app
mkdir -p /app/data /app/reports /app/logs
if [ ! -f /app/data/digest_config.json ]; then
  cp /app/digest_config.json /app/data/digest_config.json
fi

case "${1:-web}" in
  web)
    python cli.py init
    exec python -m uvicorn workspace_web:create_app --factory --host 0.0.0.0 --port 8765
    ;;
  telegram)
    python cli.py init
    exec python cli.py telegram-run --config /app/data/digest_config.json
    ;;
  scan)
    python cli.py init
    exec python cli.py scan --config /app/data/digest_config.json
    ;;
  digest)
    python cli.py init
    exec python cli.py digest --period weekly --config /app/data/digest_config.json --output /app/reports/weekly.md
    ;;
  *)
    echo "Unknown mode: $1 (expected web, telegram, scan or digest)" >&2
    exit 2
    ;;
esac
