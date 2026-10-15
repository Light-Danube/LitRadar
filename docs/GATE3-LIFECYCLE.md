# Gate 3 lifecycle closure candidate

Baseline main `20225a8e` (merged #28). [Draft PR #29](https://github.com/Light-Danube/LitRadar/pull/29) opened before subagent delegation. Version remains 0.8.0. Gate 3 closure requires actual Windows candidate results, not just authored tests.

## Implemented fixes

- Idle Telegram getUpdates/menu transport runs on a daemon worker; short main-thread waits allow prompt interruption. Only the main thread processes updates or advances offsets. Cancelled results are discarded; late transport logs/file writes are suppressed, and an outstanding request prevents a replacement poll on the same instance. No non-daemon executor exit join.
- Retry/rate-limit waits are interruptible too. Fatal 409 and other safe API diagnostics remain; active arbitrary command handlers retain their own bounded waits. An already-started remote request is not rolled back. The launcher still pauses after Python exits; an open window alone does not show a live listener.
- Scheduler remove first atomically saves the selected disabled flags. Invalid/unreadable configuration cannot silently claim success; scheduled-run fails closed, and OS removal errors are reported without re-enabling the application guard. Existing config mode/unrelated fields survive atomic replacement.
- CLI/TUI/Telegram preserve selected database/config/profile paths in registered task actions. Reinstall retains stable task names with `IgnoreNew`; per-job removal leaves the other job intact. New scheduled logs use ignored shared `log/`; historical `logs/` files remain untouched and Compose mounts both.

## Executed local evidence — 2026-10-15

- Synthetic real urllib/loopback held-response probe, pending interrupt: baseline poll **3.354s**, candidate **0.049s**; menu **3.351s → 0.005s**. Candidate 5s and 19s retry waits interrupted in about **0.051s**. These are Linux test measurements, not a diagnosis of the user's installation or a Windows timing claim.
- Eight independent shutdown cases passed: pending/OS signal, held poll/menu, retry waits, prompt process exit with a request outstanding, unchanged source bytes/mtimes/offset, no late update/log writes, error propagation and main-thread processing.
- Full `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra`: **693 passed, 0 failed, 0 skipped**, Linux Python 3.12; one existing Starlette warning. Includes scheduler lifecycle and selected-path interface regressions.
- `npm ci --prefix tests/web --ignore-scripts` (scratch cache), then `npm test --prefix tests/web`: **38 passed, 0 failed, 0 skipped**.
- Fresh extracted setup wheel installed in an isolated venv, then `scripts/built_wheel_smoke.py` outside checkout: **passed on Linux**, covering CLI/assets/web/log location/recovery. Python syntax, local documentation paths/anchors, whitespace and no-tracked-logs checks passed.

## Windows acceptance still pending

- `tests/test_telegram_shutdown.py` creates a child console and delivers actual Ctrl+C on Windows, isolated from pytest's console. Fake credentials and a loopback server only.
- `scripts/windows_scheduler_smoke.ps1` executes the production helper against JSON-backed fake cmdlets to cover absent tasks, repeated install/remove, per-job isolation, denied queries/removal/registration and selected paths.
- `scripts/windows_scheduler_native_smoke.ps1` is restricted to ephemeral GitHub-hosted Windows. It copies the helper, replaces exactly two task-name literals with generated UUID names, registers no-op actions, disables/checks/removes only those tasks, and cleans up in `finally`. It verifies native registration/settings/status/removal, not timed execution or live delivery. No default/personal tasks are touched.
- Linux has no PowerShell here. Neither harness is claimed passed until its actual Windows run succeeds. Required candidate package and regression checks also remain pending.

Gates 1–2 and provider-failure evidence remain complete. Gate 3 stays open until the above candidate checks succeed. No personal database, `.env`, token, live Telegram/provider request, major feature, merge, version bump, tag or release.
