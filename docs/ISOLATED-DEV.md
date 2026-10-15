# Isolated development for LitBeacon / Codex

## Threat model

The goal is to prevent an AI coding harness or untrusted repository code from directly modifying or reading private files on your Windows host. No container configuration can guarantee absolute host security. Prefer **Codex Cloud for changes/PRs** or **Codex CLI inside a dedicated Linux VM**. The Docker configuration in this PR is a restricted test runner, not an agent sandbox: it deliberately does not contain Codex, host Git credentials, SSH agents, API keys or a network connection.

## Recommended workflow

1. Create a dedicated Linux virtual machine (e.g. Hyper-V, VMware or VirtualBox). Do not enable shared clipboard, shared folders, USB passthrough, host SSH agents or host Docker socket mounts. Do not sign into personal browsers inside the VM.
2. In the VM, make a new clone of `Light-Danube/LitRadar` using narrowly scoped credentials, if needed. Treat source code and all downloaded artifacts as untrusted.
3. Run isolated test checks from the VM's clone:
   ```bash
   docker compose -f compose.isolated-dev.yaml config
   docker compose -f compose.isolated-dev.yaml build dev
   docker compose -f compose.isolated-dev.yaml run --rm dev
   ```
4. Codex Cloud can operate in its own remote environment and propose feature branches/PRs. Review the diff and any CI actions before merging. Do not pass your local `.env`, papers, PDF archive or production database into Codex.
5. If using **local Codex CLI**, launch it only **inside the dedicated VM**, under an unprivileged user, with its own sandbox/approval policy enabled. Keep the repository clone in the VM. The restricted Docker test runner does not grant Codex any additional host privileges.
6. Use Docker Desktop / your production Compose workflow separately for real LitBeacon data. Do not reuse test credentials or data.

## Restrictions enforced by compose.isolated-dev.yaml

- No bind mounts; no access to Windows `C:\Users` paths or host working directory at runtime.
- Source code is copied into the image at build time; `.dockerignore` excludes `.env`, databases, PDFs and caches.
- No network access **at runtime** (`network_mode: none`); image build itself needs network for installing Python packages.
- Runs as non-root UID 10001, read-only image filesystem, no Linux capabilities, no-new-privileges, limited CPU/RAM/PIDs.
- Ephemeral in-memory `/app/data`, `/app/reports`, `/app/logs` and `/tmp`: no real SQLite data is mounted; mutations vanish at container exit.
- No published ports and no Docker socket.

## Important limitations

- `docker build` and `docker compose` commands must be issued from a trusted terminal; Docker daemon access itself is powerful. Do not give untrusted agents permission to run arbitrary Docker commands against your host daemon.
- `network_mode: none` cannot prevent outbound requests at **image build time**; dependencies should be pinned/audited separately, and build inside a dedicated VM.
- A VM shares physical hardware and still has an attack surface. For the strongest boundary, do not connect shared host storage or privileged integration services.
- Tests that intentionally use external APIs will not work in this no-network runner. The image installs lightweight core/web CI dependencies, without semantic models, TUI, LLM packages or Node. Four Textual tests and one Node-dependent XML-export test are expected skips; web tests must execute. The regular CI UI/web jobs cover those optional checks. Add an explicit alternate integration test workflow rather than silently re-enabling network.
- The dev runner is intentionally **not** a replacement for the existing `compose.yaml` web + Telegram deployment or the existing Windows Scheduler.

## Data and offline tests

Use `docker compose -f compose.isolated-dev.yaml run --rm dev` to run the included test suite against ephemeral test fixtures. The default `.dockerignore` excludes the entire `data/` directory, including `data/fixture.json`. CLI smoke tests generate their own JSON under pytest's temporary directory and explicitly disable semantic model loading; the README's manual `data/fixture.json` command remains a host-checkout example.

Only `.github/workflows/tests.yml` and `release.yml` enter the image because existing contract tests read them; other `.github` files stay excluded. Source is copied with UID/GID 10001 ownership to support owner-only cloud checkout permissions. The root filesystem stays read-only and the pytest cache uses `/tmp`.

`Isolated Docker tests` builds and runs this configuration on pull requests, main pushes and manual dispatch, with read-only repository permissions. The current cloud validation used a temporary local-wheel installation override because the Docker build network lacked DNS/proxy access. See [the audit](archive/gate1/DOCKER-AUDIT.md) for executed results and remaining stock-build/CI gates.

All per-run `/app/data` state is ephemeral and never mounted from the host. The test suite includes its own fixtures where needed.

## For the next Codex session

Read `README.md`, `ROADMAP.md`, `CODEX-HANDOFF.md`, and this file. Treat `compose.isolated-dev.yaml` as the default local test environment for untrusted changes. Create a reviewable feature branch, run available offline tests, and open a draft PR; never merge automatically. Flag any task that requires local real datasets, network/API keys, broader filesystem privileges or Docker daemon access.
