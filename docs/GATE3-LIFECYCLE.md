# Gate 3 lifecycle closure

Baseline main `20225a8e` (merged #28). [Draft PR #29](https://github.com/Light-Danube/LitRadar/pull/29) opened before subagent delegation. Version remains 0.8.0. Gate 3 is complete for this bounded local-only candidate, using the executed evidence below. Final documentation-head CI remains tracked in PR #29; this is not release/version approval.

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

## Actual Windows acceptance

- Actual [Windows lifecycle/interface step](https://github.com/Light-Danube/LitRadar/actions/runs/38799700853/job/116645218528) passed **37 tests, zero failures/skips** at runtime implementation head `845a6255`, including a child console delivering real Ctrl+C, pending-interrupt/blocked-loopback cases, scheduler failure guards and selected-path interfaces. Later changes are PowerShell-harness/workflow corrections; runtime code is unchanged. Fake credentials and loopback only.
- Actual [Windows PowerShell 5.1 scheduler checks](https://github.com/Light-Danube/LitRadar/actions/runs/38800665436/job/116648524877) succeeded at `6ed0fc8d`. The isolated harness executes the production helper against JSON-backed fake cmdlets for absent tasks, repeat install/remove, per-job isolation, denied query/removal/registration and selected paths. Child-process state is isolated, and collections retain array shape in PowerShell 5.1.
- The native harness in that same actual successful Windows run is restricted to ephemeral GitHub-hosted Windows. It copies the helper, replaces exactly two task-name literals with generated UUID names, registers no-op actions, disables/checks/removes only those tasks, and cleans up in `finally`. It verifies native registration/settings/status/removal, not timed execution or live delivery. No default/personal tasks are touched.
- PowerShell was unavailable locally; the above passing claims come from actual Windows steps. The enclosing recovery/browser workflow and final documentation-head checks were still running when recorded. Consult PR #29 for final status rather than inferring a full candidate pass from targeted steps.

Gates 1–3 are complete for this candidate within the stated synthetic/native-registration limits. Gates 4–6, final release approval/versioning and any reproduced new defect remain separate. No personal database, `.env`, token, live Telegram/provider request, major feature, merge, version bump, tag or release.
