# LitBeacon 1.0 — active release checklist

Baseline main `2130f707` (merged PR #33). Version stays **0.8.0**; no merge/tag/release authorization is implied.

- **Gate 1: closed.** [Archived feature inventory and closure evidence](archive/gate1/release-checklist-2026-10-15.md). Windows daily use and optional Narrator were accepted by the user; automated results remain separate.
- **Gate 2: complete for this candidate.** Read-only SQLite backup, new-destination restore, elected artifacts/checksums and legacy upgrade are tested. Actual [Ubuntu/Windows extracted setup-wheel recovery checks](https://github.com/Light-Danube/LitRadar/actions/runs/38744388702) passed at implementation head `a9c64fb2`; no personal data or services were used.
- **Gate 3: complete for this candidate.** Clean package/daily-use/provider-preservation evidence plus Windows lifecycle/interface and native scheduler registration/remove checks. [Closure and limits](GATE3-LIFECYCLE.md). PR #29 head `883b90e5` had 20/20 successful checks; no timed live delivery, universal listener lock or instant cancellation of arbitrary active commands is claimed.
- **Gate 4: complete for the bounded candidate.** [Loopback launch](GATE4-LOCAL-BOUNDARY.md), [Research paths](GATE4-RESEARCH-PATHS.md), [upload/restore acceptance](GATE4-IMPORT-RESTORE-PATHS.md), [SQLite/manual-data integrity](GATE4-INTEGRITY-CLOSURE.md) and [network-use documentation](NETWORK-USE.md) have explicit local evidence/limits. Contradictory identifiers reject, canonical provider pairs survive refresh, and missing models do not trigger weight downloads. No complete security audit or new Windows/CI result is claimed.

- **Gate 5: in progress.** [Annotation editor keyboard focus](GATE5-KEYBOARD-FOCUS.md) is the first bounded EN/UK web slice. Broader web/TUI keyboard, scrolling/error handling and ordinary-user Research workflow evidence remain open. Narrator remains optional with the recorded user acceptance; no certification is inferred.

- Gates 5–6 remain governed by [ROADMAP](../ROADMAP.md), including existing keyboard/usability evidence and final release approval.

## Current small Draft PR #34

1. Reproduce and fix focus on explicit annotation Edit and focus return on Cancel/Escape.
2. Check EN/UK handlers, composition-safe Escape, no cancel mutation and preservation of unrelated drafts without focus theft on restoration.
3. Execute local checks. Hosted Actions are deferred by explicit user instruction: the supplied GitHub annotation confirms account payment/spending-limit blocking before any job steps. Main's merge tree is identical to passing PR #29; this is not an executed-test failure. No further CI retries or billing/workflow changes.

No new subsystem, personal database access, version bump or automatic merge. Next small slice: existing TUI EN/UK modal navigation, help scrolling, close/cancel focus and persistent errors; Research discoverability/save/export evidence also remains Gate 5 work.

## Historical Gate 2 validation — 2026-10-15 (PR #26)

- Linux Python 3.12: `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra` — **518 passed, 0 failed, 0 skipped**; one existing Starlette deprecation warning.
- `npm ci --prefix tests/web --ignore-scripts` (shared scratch cache), then `npm test --prefix tests/web` — **38 passed, 0 failed, 0 skipped**.
- `python -m pip wheel --no-deps --no-build-isolation --wheel-dir work/wheels .`; `python -m scripts.build_user_bundle ... --output-dir work/bundles`; extract ZIP, create fresh venv, install extracted wheel `[web]` plus smoke-only `httpx`, execute `scripts/built_wheel_smoke.py` from outside checkout — **passed on Linux**, including recovery CLI, exact durable table/history/tombstone comparison, elected files/checksums, integrity and no overwrite. FTS-derived tables are excluded from row comparison; legacy upgrade is covered by source tests.
- Documentation link/anchor scan: **221 targets resolved**; `python -m py_compile scripts/built_wheel_smoke.py` and `git diff --check` passed.
- Actual [Ubuntu/Windows installed-wheel CI](https://github.com/Light-Danube/LitRadar/actions/runs/38744388702) **succeeded** at implementation head `a9c64fb2`. Both job logs report the recovery round-trip and general CLI/assets/web/edit/restart smoke passed; reviewable setup ZIP artifacts uploaded. This closes Gate 2 package evidence. Final head `430ffcf0` had 20/20 successful checks before PR #26 was merged. This is not release approval.

Previous candidates: [Gate 3 lifecycle closure](GATE3-LIFECYCLE.md). Actual Windows 37-test shutdown/interface checks and PowerShell native/failure contracts passed, along with local 693 Python / 38 JS checks. All 20 checks passed on final PR #29 head before merge. Gate 4 PR #30 passed 702 Python / 38 JS, PR #31 passed 713 Python / 38 JS, PR #32 passed 723 Python / 38 JS and [Gate 4 closure PR #33](GATE4-INTEGRITY-CLOSURE.md) passed 732 Python / 38 JS tests locally. Current [Gate 5 focus evidence](GATE5-KEYBOARD-FOCUS.md) records this increment. Hosted CI remains deferred.
