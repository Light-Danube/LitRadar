# Docker / Docker Compose — LitBeacon (preview)

This is an **optional, local-only deployment** for LitBeacon v0.8.x. It does not replace the existing Windows CLI/TUI workflow. It deliberately reuses the **same SQLite database** under `./data`.

## Prerequisites

- Docker Desktop with Docker Compose v2 on Windows (or Docker Engine + Compose on Linux).
- Enough disk space for the core Python dependencies (including the semantic-model stack); the initial image can be large.
- From the repository root, copy `.env.example` to `.env` if you do not already have it. Keep `.env` private, and enter the API keys/Telegram token only when needed.
- Before your first run with real data, **back up `data/litradar.sqlite3`** and `digest_config.json`. Do not run host and container migrations concurrently.

## Start the web workspace

```powershell
docker compose up --build -d web
docker compose ps
docker compose logs -f web
```

Open <http://127.0.0.1:8765>. The service binds to `0.0.0.0` inside the container so Docker can forward traffic, but Compose publishes only to host loopback `127.0.0.1`. **Do not change this mapping to `0.0.0.0` or expose the port publicly**: the current web API has no authentication.

Stop the services with `docker compose down`. This does **not** delete `./data`, `./reports`, `./logs` or your `digest_config.json`. Avoid `docker compose down -v` as a default habit.

## CLI, scans, reports

```powershell
docker compose run --rm --no-deps web python cli.py stats
docker compose run --rm --no-deps web python cli.py scan
docker compose run --rm --no-deps web python cli.py digest --period weekly --output reports/weekly.md
docker compose run --rm --no-deps web python -m pytest -q
```

The image installs `requirements.txt` and `requirements-web.txt` only. For tests, TUI and optional LLM providers, create a separate development image or install additional `requirements-dev.txt`, `requirements-ui.txt`, `requirements-llm.txt`; the `pytest` command above requires dev dependencies and **will not work** in the default runtime image. Run tests on the host after installing dev dependencies.

The mounted `./data` directory stores SQLite database, offline PDFs, provider caches and Telegram update offsets. The `./reports` and `./logs` directories persist too. `digest_config.json` is mounted as a writable file so Telegram controls can persist configuration changes. `research_profile.json` comes from the image; rebuild after editing it or add a mount intentionally.

## Telegram bot (optional)

```powershell
docker compose --profile bot up -d telegram
docker compose --profile bot logs -f telegram
docker compose --profile bot stop telegram
```

The bot uses long polling and the same private `LITRADAR_TELEGRAM_* ` variables from `.env`. **Stop your Windows `run_telegram_bot.bat` process before starting this container**. Telegram permits only one active `getUpdates` poller per token.

## Scheduling is not automatically migrated

A running container is not itself a scheduler. The existing `install_schedule.bat` registers **Windows** Task Scheduler jobs and does not configure Docker. Do not blindly enable both Windows jobs and container jobs: doing so can duplicate scans/digests.

If you want regular unattended execution, configure **one** host scheduler to invoke a one-off container for `python cli.py scan` and `python cli.py digest --period weekly --send`. For true remote 24/7 availability, deployment, authentication and backup/synchronization need a separate design; this local Compose file is not a hosted SaaS setup.

## Troubleshooting

- `docker compose config`: validate Compose variable expansion and structure.
- `docker compose ps`: check the health status.
- `docker compose logs --tail 100 web`: view server startup errors.
- Ensure `.env` exists and is readable.
- If SQLite is read-only on Linux, ensure the UID running the container can write to mounted `data/`; never fix this by making the database world-writable.
- If another process uses port 8765, stop it or change the **host-side** port only (e.g. `127.0.0.1:8766:8765`).
- No files in `./data`, `.env`, `./logs` or `./reports` are baked into the image because `.dockerignore` excludes them.

## Release gate

The Docker/Compose files should be validated with `docker compose config`, `docker compose build`, `docker compose up -d web`, a GET to `http://127.0.0.1:8765/api/health`, and an actual paper list request before merging. If these steps cannot be performed in the contributor's environment, keep the PR as draft.
