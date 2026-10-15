# LitBeacon Docker integration handoff

PR #5 is merged and adds an **optional** Docker Compose launch path for the v0.8.x local web workspace.

- The browser runs on host `127.0.0.1:8765`; Uvicorn binds all interfaces only *inside* the container. The browser has no authentication, so the host binding is intentionally loopback-only.
- Runtime image installs core + web requirements; dev/UI/LLM dependencies are not installed.
- Host bind mounts preserve `data/`, `reports/` and `logs/`. The image build excludes `.env` and user state.
- The boot helper copies `digest_config.json` to `data/digest_config.json` once. Docker's config is separately editable because Telegram writes configuration with an atomic file replacement, which fails with a single-file bind mount.
- Telegram listener is an optional Compose profile; do not run it alongside the Windows bot listener using the same token.
- Existing Windows scheduler is **not automatically migrated**; avoid duplicate scan/digest jobs. Explicit one-off container commands are documented in `DOCKER.md`.
- Offline file-contract tests: `python -m pytest -q tests/test_docker_contract.py`.
- A manually triggered GitHub Actions workflow `Docker smoke (manual)` builds the image and checks the HTTP health endpoint.

**Release gate:** The latest cloud audit has Docker Engine, but stock image builds cannot reach PyPI from the build network. A lightweight dev image built from local wheels ran the restricted suite and served synthetic web/API requests; this does not validate the production `Dockerfile` image or current GitHub CI. See `docs/archive/gate1/DOCKER-AUDIT.md`. Run the manual production-image workflow or Docker Desktop checks before declaring Docker deployment stable. Do not market this as a public deployment; authentication, secure scheduler, backups and hardening remain work to do.
