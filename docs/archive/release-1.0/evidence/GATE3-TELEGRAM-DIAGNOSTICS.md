# Gate 3 increment — Telegram listener diagnostics

Baseline main `044358b8` (merged #26). Gates 1–2 are complete; [Draft PR #27](https://github.com/Light-Danube/LitRadar/pull/27) is one focused Gate 3 increment, not full Gate 3 or release approval. Version remains 0.8.0. The draft was opened before subagent delegation.

## Implemented scope

- Typed fatal polling errors stop with CLI exit 2, including HTTP/JSON 409 conflict. Guidance distinguishes another poller from an existing webhook; neither is changed automatically. Transient retries, Ctrl+C (including backoff), nonfatal command-menu setup and existing offsets remain.
- Fixed actionable messages explain 400/401/403/404/409/429/5xx, timeout/DNS/proxy/TLS and invalid responses. Known fatal status survives a failure reading/closing its error body. Valid 429 waits of 1–3600 seconds are honored; missing/invalid waits use five seconds; longer requested waits stop for manual retry.
- Scoped timestamped console diagnostics, optional `--debug` API method/outcome/status/timing, and opt-in `--log-file PATH` UTF-8 rotation (1 MiB, three backups). No implicit file or root-logger reconfiguration. Listener diagnostics and caught-exception replies/failure records omit token-bearing URLs, credentials, IDs, bodies, private content and raw exceptions.
- Fake HTTP/API/logging/CLI tests cover poisoned error text, failure preservation, interruption and logger cleanup. A dedicated Windows workflow step executes these tests with synthetic credentials only.

## Executed local evidence — 2026-10-15

- Final combined `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra`: **589 passed, 0 failed, 0 skipped**, Linux Python 3.12; one existing Starlette deprecation warning. Includes 62 diagnostics and nine CLI regression cases in addition to the prior suite.
- `npm ci --prefix tests/web --ignore-scripts` (scratch cache), then `npm test --prefix tests/web`: **38 passed, 0 failed, 0 skipped**.
- Final `python -m pip wheel --no-deps --no-build-isolation ...`, setup bundle build, wheel installation in an isolated venv and `scripts/built_wheel_smoke.py` outside the checkout: **passed on Linux**, including CLI/defaults/static assets/web edit/restart and backup/restore. This existing smoke does not establish live Telegram behavior; fake-transport source tests cover the listener change.
- Changed Python files compiled; documentation scan resolved **231 local links/anchors**; `git diff --check` passed. Independent code review found and verified fixes for lost HTTP status on body-read failure and premature retry of oversized rate-limit waits.
- Actual [Ubuntu/Windows installed-wheel CI](https://github.com/Light-Danube/LitRadar/actions/runs/38755491415) succeeded at implementation head `ed87c805`, including installed recovery and general CLI/assets/web smoke.
- The actual [Windows listener diagnostics step](https://github.com/Light-Danube/LitRadar/actions/runs/38755491462/job/116492685489) succeeded at the same implementation head, using fake credentials only. The enclosing recovery/browser workflow was still running when this evidence was recorded; its final result and later documentation-head checks are tracked in PR #27. Linux is not Windows evidence.

## Boundaries and next increments

[Operator troubleshooting](../../../TELEGRAM-TROUBLESHOOTING.md) records retry/exit behavior and logging limits. This is remote conflict handling, not a cross-machine ownership lock or guaranteed command replay. Existing provider scan summaries, scheduler subprocess results, independent digest delivery and `telegram-chats` transports retain separate diagnostics. No blanket application-wide sanitization or debug logging claim is made.

Gate 3 remains open for scheduler disable/remove verification and source timeout/429/offline preservation through continued local workspace read/edit/export. A next small diagnostics PR can improve safe provider HTTP messages alongside that failure-preservation evidence. No live credentials, personal databases, major features, version bump, merge or release.
