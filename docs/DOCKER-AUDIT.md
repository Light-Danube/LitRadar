# Docker development audit — 2026-10-13

## Repository and CI evidence

The checkout and remote main both point to `7b4034d0`. Git history confirms PR #5 merged as `ccbe6a68`, and PR #6 merged as `7b4034d0`, including fix `be9b230`. Remote PR-head refs agree. The only advertised branch is main; no other feature branch was assumed merged.

GitHub REST and GraphQL operations return `Forbidden`, including after a scoped permission retry. Git read access works, but does not establish GitHub API or PR-write access. Current CI results, historical failure logs and the full open-PR list could not be retrieved. No claim is made that all six historical failures shared one cause. The old `ports:` substring assertion does match `/app/reports:rw`; the anchored mapping-key check correctly rejects that false positive.

## Executed checks

| Check | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| Main baseline, Python 3.12 with UI/web dependencies | 143 | 0 | 0 |
| Patched full suite, Python 3.12 with UI/web dependencies | 144 | 0 | 0 |
| Patched JavaScript tests, Node 24 | 4 | 0 | 0 |
| Restricted dev container, Python 3.11, local-wheel build | 139 | 0 | 5 |

The lightweight core-only CI dependency profile produced 119 passes and six expected skips before the new contract test: two absent-FastAPI module skips and four Textual skips. This reproduces an optional-dependency skip profile; it does not substitute for the unavailable historical logs. The restricted web-capable image skips only four Textual tests and the Node-dependent XML export test. No unexplained skips remain in the locally executed profiles.

JavaScript syntax checks passed. Isolated Compose validation passed. Production Compose validation uses a temporary override clearing both services' `env_file` entries so no personal `.env` is read or required. Production services with host data mounts were not started.

Docker Engine 28.4.0 and Compose 2.40.3 are available. A stock dev build failed at PyPI DNS resolution; passing standard build proxy arguments also failed to resolve the proxy. A temporary build-only proxy hostname mapping reached the proxy, but TLS rejected its certificate chain. No runtime network restriction or verification setting was relaxed, and no host trust files were accessed. For container validation only, wheels were downloaded through the cloud machine's working PyPI route and installed with `--no-index` in a generated build context under ignored `.venv/`. The original base image was retained; dependency installation used a temporary Dockerfile override and `docker build --network none`. This validates the container test/runtime configuration, not the stock online build path or the production `Dockerfile` image.

The dev image's web boot helper initialized a disposable tmpfs database, ingested a synthetic paper, and returned HTTP 200 with validated content from `/`, `/api/health`, `/api/summary` and `/api/papers`. No external providers, Telegram delivery or production databases were used.

## Fixes and security review

- CLI smoke tests previously required the excluded `data/fixture.json`. They now generate disposable JSON and explicitly use `--no-semantic`; tests still exercise ingestion, ranking, export and offline metadata.
- Two existing contract tests require CI YAML files previously excluded by `.dockerignore`. Only `tests.yml` and `release.yml` are included; research data, secrets and all other workflow files remain excluded.
- Cloud source files have owner-only permissions. The first non-root container attempt failed before collection with `PermissionError` on `/app/pyproject.toml`. Copying source with UID/GID 10001 ownership fixes this without root tests or world-readable source.
- The dev image uses the lightweight web CI dependencies; tests use synthetic embeddings and do not need heavyweight semantic models. Pytest cache is placed on ephemeral `/tmp`.
- A PR workflow builds and runs the isolated image with read-only GitHub permissions. Remote execution has not been observed in this session.

Inspection of the actual container confirmed network mode `none`, user `10001:10001`, read-only root, all capabilities dropped, no-new-privileges, no privileged mode, no host binds and no published ports. Only disposable tmpfs state is writable. No Docker socket or personal host directory is mounted. Docker daemon access and the cloud harness remain separate trust boundaries.

Production Compose has intentionally persistent repository-relative data/report/log mounts and shared `.env` injection. It binds the unauthenticated web service to host loopback; the Telegram service is opt-in. Its runtime image still runs as root and does not inherit the dev runner's restrictions. Those deployment hardening limitations remain explicit; applying non-root deployment changes needs separate bind-mount permission/migration validation. Do not use production Compose for untrusted tests or expose its web service publicly.

## Remaining gates

Obtain scoped GitHub API access to inspect every historical failed/skipped job, observe current CI, list open PRs and create the requested draft PR. Existing GitHub proxy/token bindings were checked; no new token values were requested. Run the stock isolated build in a working build-network environment and run the manual production Docker smoke workflow against synthetic data. Windows/Docker Desktop validation remains outstanding. No PR was merged and no deployment was performed.
