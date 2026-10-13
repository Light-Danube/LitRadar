# LitBeacon: Docker quick start

This is an **optional localhost deployment** for the existing Python/SQLite application. It does not replace the Windows scripts or provide remote/public authentication.

## Start

1. Install Docker Desktop (Windows) with Compose v2.
2. Back up your existing `data/litradar.sqlite3` and `digest_config.json`.
3. Copy `.env.example` to `.env` (unless you already have one). Keep secrets out of Git.
4. In the repository root run:

```powershell
docker compose up --build -d web
docker compose ps
docker compose logs -f web
```

Open <http://127.0.0.1:8765>. Compose forwards only host loopback to the web process listening on the container's network. **Do not publish the web port publicly**: the current web UI has no authentication.

`docker compose down` stops services but leaves host `data/`, `reports/`, `logs/` intact. Never delete these folders during an upgrade.

The first container start copies the repository's `digest_config.json` into `data/digest_config.json` if absent. After that, **the copy in `data/` is authoritative inside Docker**. This avoids unsafe bind-mounting an individual JSON file that the Telegram bot atomically replaces. Edit `data/digest_config.json` for container use. Docker and host Windows launchers do *not* automatically share subsequent digest-config edits.

## CLI and reports

```powershell
docker compose run --rm --no-deps web python cli.py stats
docker compose run --rm --no-deps web sh /app/docker/boot.sh scan
docker compose run --rm --no-deps web sh /app/docker/boot.sh digest
```

The scan command uses `data/digest_config.json`. The digest command saves a weekly Markdown report under `reports/`, and does not send a Telegram message. To send an immediate digest use:

```powershell
docker compose run --rm --no-deps web python cli.py digest --period weekly --config data/digest_config.json --send
```

## Interactive Telegram bot

```powershell
docker compose --profile bot up -d telegram
docker compose --profile bot logs -f telegram
docker compose --profile bot stop telegram
```

The listener is optional; it shares the same persistent `data/` with the web service. Do not run `run_telegram_bot.bat` simultaneously with the container bot using the same token, because Telegram permits only one active `getUpdates` consumer per bot.

**Scheduling:** Docker does not automatically create Windows Task Scheduler tasks. Configure **one** host scheduler to launch the one-off `boot.sh scan` and `boot.sh digest` commands if you need periodic unattended runs. Avoid running Windows scheduled scans and Docker scheduled scans on the same database simultaneously. On a permanently running VPS, introduce authorization and backups before making anything publicly reachable.

## Requirements, tests and limitations

PR #5 is merged, but production-image build/run remains a release gate. The cloud audit validated the boot helper using an isolated dev image and synthetic data; Docker build networking prevented a stock production-image build. See [the audit](docs/DOCKER-AUDIT.md) for the precise scope. Production Compose intentionally mounts host research data and reads `.env`; never use it as the untrusted development test runner.

The runtime image installs `requirements.txt` and `requirements-web.txt`. It does not install Textual, pytest or optional LLM extras; this keeps its footprint smaller, though `sentence-transformers` may still be large. To run regression tests on your development machine install `requirements-dev.txt` and run `python -m pytest -q`. Confirm the container with:

```powershell
docker compose config
docker compose build web
docker compose up -d web
docker compose ps
docker compose exec web python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8765/api/health').read().decode())"
```

Linux bind-mount permissions may require matching the host UID/GID; avoid making private research data world-writable. Docker does not change the design assumption that the web app is local-only and single-user.
