# LitBeacon 1.0 — active release checklist

Baseline main `4dce7638` (merged PR #30). Version stays **0.8.0**; no merge/tag/release authorization is implied.

- **Gate 1: closed.** [Archived feature inventory and closure evidence](archive/gate1/release-checklist-2026-10-15.md). Windows daily use and optional Narrator were accepted by the user; automated results remain separate.
- **Gate 2: complete for this candidate.** Read-only SQLite backup, new-destination restore, elected artifacts/checksums and legacy upgrade are tested. Actual [Ubuntu/Windows extracted setup-wheel recovery checks](https://github.com/Light-Danube/LitRadar/actions/runs/38744388702) passed at implementation head `a9c64fb2`; no personal data or services were used.
- **Gate 3: complete for this candidate.** Clean package/daily-use/provider-preservation evidence plus Windows lifecycle/interface and native scheduler registration/remove checks. [Closure and limits](GATE3-LIFECYCLE.md). PR #29 head `883b90e5` had 20/20 successful checks; no timed live delivery, universal listener lock or instant cancellation of arbitrary active commands is claimed.
- **Gate 4: in progress.** [Local web launch boundary](GATE4-LOCAL-BOUNDARY.md) is verified locally; [Research result path safeguards](GATE4-RESEARCH-PATHS.md) address linked files and Windows reparse paths. Upload/restore paths, SQLite preservation and network-use checks remain open; no complete security audit or new Windows verification is claimed.

- Gates 4–6 remain governed by [ROADMAP](../ROADMAP.md), including focused safety checks and final release approval.

## Current small Draft PR #31

1. Reproduce and reject linked Research artifact/manifest files, preserving normal immutable bundles and exports.
2. Reject Windows reparse points throughout Research paths, including parent junctions, with independent disposable regression fixtures.
3. Execute local checks. Hosted Actions are deferred by explicit user instruction: the supplied GitHub annotation confirms account payment/spending-limit blocking before any job steps. Main's merge tree is identical to passing PR #29; this is not an executed-test failure. No further CI retries or billing/workflow changes.

No new subsystem, personal database access, version bump or automatic merge. Next small slice: Gate 4 upload/restore path safeguards with disposable fixtures before closing the broader filesystem checklist item.

## Historical Gate 2 validation — 2026-10-15 (PR #26)

- Linux Python 3.12: `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra` — **518 passed, 0 failed, 0 skipped**; one existing Starlette deprecation warning.
- `npm ci --prefix tests/web --ignore-scripts` (shared scratch cache), then `npm test --prefix tests/web` — **38 passed, 0 failed, 0 skipped**.
- `python -m pip wheel --no-deps --no-build-isolation --wheel-dir work/wheels .`; `python -m scripts.build_user_bundle ... --output-dir work/bundles`; extract ZIP, create fresh venv, install extracted wheel `[web]` plus smoke-only `httpx`, execute `scripts/built_wheel_smoke.py` from outside checkout — **passed on Linux**, including recovery CLI, exact durable table/history/tombstone comparison, elected files/checksums, integrity and no overwrite. FTS-derived tables are excluded from row comparison; legacy upgrade is covered by source tests.
- Documentation link/anchor scan: **221 targets resolved**; `python -m py_compile scripts/built_wheel_smoke.py` and `git diff --check` passed.
- Actual [Ubuntu/Windows installed-wheel CI](https://github.com/Light-Danube/LitRadar/actions/runs/38744388702) **succeeded** at implementation head `a9c64fb2`. Both job logs report the recovery round-trip and general CLI/assets/web/edit/restart smoke passed; reviewable setup ZIP artifacts uploaded. This closes Gate 2 package evidence. Final head `430ffcf0` had 20/20 successful checks before PR #26 was merged. This is not release approval.

Previous candidate: [Gate 3 lifecycle closure](GATE3-LIFECYCLE.md). Actual Windows 37-test shutdown/interface checks and PowerShell native/failure contracts passed, along with local 693 Python / 38 JS checks. All 20 checks passed on final PR #29 head before merge. Gate 4 local-launch PR #30 passed 702 Python / 38 JS tests locally; [current Research path evidence](GATE4-RESEARCH-PATHS.md) records this increment. Hosted CI remains deferred.
