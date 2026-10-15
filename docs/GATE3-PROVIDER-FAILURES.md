# Gate 3 increment — provider failures and log location

Baseline main `4e2486d3` (merged #27 plus owner `.gitignore` update). [Draft PR #28](https://github.com/Light-Danube/LitRadar/pull/28) opened before delegation. Version remains 0.8.0.

## Implemented scope

- Fixed actionable provider HTTP/network diagnostics replace raw exception text in registry progress, pipeline summaries, citation-fetch error history, scan failure summaries and Research API transport errors. Retry behavior, original exceptions, partial success and existing API status identifiers remain.
- Synthetic outages cover 403/404/429/503, timeout and offline conditions. Tests retain durable notes/tags/status/IDs, relations/feedback, annotations/evidence histories/tombstones and preset deletions; then execute local workspace read/edit/evidence export/reopen. Partial-provider success retains manual fields; scan/citation failures add only their explicit safe history records.
- Shared `LOG_ROOT = WORKSPACE_ROOT/log` and `resolve_log_path()` establish the rule for all new/extended file logging across CLI, web, TUI, Telegram and providers. Telegram filename/path handling uses it; console-only use creates no directory. Reject outside/traversal/link/reparse paths and linked rotation siblings.
- Git/Docker exclusions cover `log/`, legacy `logs/`, `*.log` and `*.log.*`; validated setup wheels reject log directories/rotated files. Preserve owner ignore rules and legacy scheduled-job locations. No existing files are moved.

## Executed local evidence — 2026-10-15

- `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra`: **656 passed, 0 failed, 0 skipped**, Linux Python 3.12; one existing Starlette warning. Includes 44 provider-preservation/diagnostics cases, 19 log-path cases and four additional package exclusion cases.
- `npm ci --prefix tests/web --ignore-scripts` (scratch cache), then `npm test --prefix tests/web`: **38 passed, 0 failed, 0 skipped**.
- Build wheel and lightweight setup ZIP, extract it, create a fresh venv, install extracted `[web]` wheel plus smoke-only `httpx`, execute `scripts/built_wheel_smoke.py` outside checkout: **passed on Linux**. Verifies installed writable `log/`, logger closure/outside-path rejection, CLI/assets/web edit/restart and recovery. No live provider/Telegram call.
- Changed Python files compiled; local documentation paths/anchors and `git diff --check` passed. `git ls-files` found no tracked `log/`, `logs/`, `.log` or rotated `.log.*` files. Actual Git ignore checks use a disposable repository; Docker/wheel exclusions have separate contracts.
- Independent read-only review found no blocker. Candidate Windows provider/log-path checks and Ubuntu/Windows installed package checks remain pending until observed.

## Boundaries

[Shared logging policy and locations](LOGGING.md) apply to all further logging development; this increment does not enable a global file logger. Existing stored query/configuration context, provider results, offline-download reports, independent digest/chat-discovery transports and scheduler subprocess output retain their separate behavior. No claim that every application output is sanitized.

Gate 3 provider-failure closure requires actual Windows evidence; scheduler disable/remove remains separate. No personal databases, credentials, external provider requests, model loads, major feature, merge, bump or release.
