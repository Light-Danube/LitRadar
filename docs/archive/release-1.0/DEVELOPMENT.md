# Development reference

Maintainer setup, CI and architecture notes. For ordinary use, start with the [user guide](../../USER-GUIDE.md).

## Development and CI

[Network-use reference](../../NETWORK-USE.md) lists which searches, scheduled jobs, Telegram actions, downloads and optional inference contact services and what they send. Local library storage does not make every optional workflow offline. Legacy CLI/TUI semantic ranking loads only a pre-provisioned local/cached model; set the profile's `embedding_model` to a trusted local model directory or use `--no-semantic` for CLI keyword scoring. Missing models fall back to keywords without downloading weights. The optional web semantic workspace has its separate, stricter local-path/safetensors setup.

Run:

```bash
python -m pytest -q
```

GitHub Actions contains core, Textual UI, and browser-workspace test jobs. The web job installs `requirements-web.txt` and checks the JavaScript bundle syntax with Node. DOM regression tests use a locked, test-only jsdom installation: `npm ci --prefix tests/web --ignore-scripts` then `npm test --prefix tests/web`. This does not add a production Node runtime or build step. Dependency-free graph/localization/palette tests can also run with `node --test tests/test_web_frontend.cjs`. The tests are configured through `pyproject.toml` so imports do not depend on the directory from which pytest was started.

## Architecture

```text
                    source registry
              ┌─────────┼─────────┐
              ↓         ↓         ↓
          OpenAlex   Semantic    arXiv
                       Scholar
              └─────────┼─────────┘
                        ↓
                 retry + cache
                        ↓
                normalized Papers
                        ↓
             keyword + semantic rank
                        ↓
                    SQLite
                        ↓
          ┌─────────────┼──────────────┐
          ↓             ↓              ↓
        CLI            TUI           offline
          └─────────────┼──────────────┘
                        ↓
              explicit user feedback
                        ↓
               personal ranking
                        ↓
                optional LLM triage
```

## Roadmap

The archived [UI/UX research](../gate1/ux-research/README.md) includes a standalone concept, the 48-item feature-preservation checklist, and an incremental plan. [Phase 1](../gate1/ux-research/phase-1.md) implements the theme and responsive shell foundation. [The public-source competitor review](../gate1/ux-research/live-review-2026-10-13.md) now uses accessible official pages; its original hands-on competitor, browser and participant limitations remain recorded separately from later user acceptance and CI evidence.

Release status and remaining work are maintained in [`ROADMAP.md`](../../../ROADMAP.md) and the [active checklist](../../LOCAL-1.0-RELEASE-CHECKLIST.md). The [Gate 1 archive](../gate1/README.md) holds completed feature history and design proposals. Optional semantic exploration remains experimental; historical real-model evaluation limits do not introduce a new release blocker.

## Changelog

See [`CHANGELOG.md`](../../../CHANGELOG.md) for the release history.


## Isolated development with Codex

For security-conscious development, the repo includes an opt-in **offline Docker test runner**: `docker compose -f compose.isolated-dev.yaml run --build --rm dev`. It runs without network, bind mounts, host secrets, or privileged access. This protects the **test process**; it does not sandbox Codex itself or the Docker daemon. Run Codex CLI inside a dedicated Linux VM without Windows shared folders, or use Codex Cloud with narrowly scoped GitHub access. See [docs/ISOLATED-DEV.md](ISOLATED-DEV.md) for the threat model, safeguards and limitations.

The dev image uses lightweight core/web CI dependencies, disposable CLI fixtures, and a writable pytest cache under `/tmp`. Optional Textual/Node checks remain covered by the regular CI jobs. The `Isolated Docker tests` workflow builds and runs the restricted image on PRs. See [the Docker audit](../gate1/DOCKER-AUDIT.md) for executed checks and outstanding production-image/remote-CI gates.
