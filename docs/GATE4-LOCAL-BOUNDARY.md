# Gate 4 — local web launch boundary

Small first slice of Gate 4, based on main `bc9cbde7` (merged PR #29). Version remains 0.8.0. Scope: the existing CLI's loopback-only web launch, its source launcher and the documented Docker host-port boundary. Path/upload/export and SQLite integrity checks remain separate Gate 4 work.

## Verified boundary

- The existing CLI defaults to numeric `127.0.0.1`, accepts only that address or `localhost`, and passes its selected host explicitly to Uvicorn. `UVICORN_HOST=0.0.0.0` does not override it. Selected database, port and browser choice are preserved.
- Argparse and the separate command guard reject IPv4/IPv6 wildcard, IPv6 loopback (unsupported by this CLI), LAN/example addresses and arbitrary hostnames. Direct command rejection occurs before app/database creation, browser opening or server start. This does not promise that `run_web.bat` performs no initialization: it runs setup first, then forwards arguments to the CLI.
- A child launches the real CLI with its default host and ephemeral port, a disposable library and user root, and browser opening disabled. A Uvicorn startup observer records the actual listening sockets without replacing binding or selecting the address/port. The test requests health and an empty-library summary over loopback, then terminates and reaps the child. No personal database or live provider request.
- Static Compose checks require exactly the shipped host-loopback publication and reject additional mappings/host networking. Docker's boot script/image deliberately use container-internal `0.0.0.0`; the host boundary is Compose's `127.0.0.1:8765:8765`. Docker itself was not run in this increment.

## Executed local evidence — 2026-10-16

- `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra tests/test_web_launch_boundary.py tests/test_docker_contract.py`: **13 passed, zero failed/skipped**, Linux Python 3.12. Independent read-only subagent review checked entry points and scope; the socket observer also avoids assuming a Python-level bind hook with optional uvloop. uvloop itself and Windows were not separately executed.
- Full `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra`: **702 passed, zero failed/skipped**, Linux Python 3.12; one existing Starlette warning. No application runtime code, configuration or version change.
- `npm ci --prefix tests/web --ignore-scripts` (scratch cache), then `npm test --prefix tests/web`: **38 passed, zero failed/skipped**. No JavaScript was changed.
- Python syntax, **116 local documentation targets/anchors**, `git diff --check` and no-tracked-logs checks passed. Generated test output stays in ignored scratch directories; application file logging remains under ignored shared `log/`.

GitHub-hosted Actions are deferred at the user's request because account billing prevents jobs starting. The user supplied the exact payment/spending-limit annotation; main `bc9cbde7` and previously passing PR #29 head `883b90e5` have identical Git trees. A single main Windows retry also stopped before any steps. These failed/canceled startup checks are not application test results. No workflow disabling, billing changes, extra CI retries or new CI/Windows pass claim.

## Limits and next slice

Loopback binding is a launch restriction, not authentication, Origin/Host validation, CSRF or DNS-rebinding protection, or protection against other programs/users on the same computer. Direct Uvicorn invocation, edited Docker publication, reverse proxies and tunnels can bypass the documented launch restriction; public/LAN service is outside the supported local-only setup. The `localhost` alias is forwarded to the operating system; the real-socket probe verifies the numeric default, not every host resolver configuration.

Only Gate 4's default/local-launch checklist item is closed. Next small PR: exercise Research result path/symlink and export safeguards with disposable fixtures. Upload/restore paths, SQLite preservation, network-use documentation, remaining Gates 4–6 and final release approval stay separate. No complete security audit, authentication subsystem, personal data access, merge or version bump is claimed.
