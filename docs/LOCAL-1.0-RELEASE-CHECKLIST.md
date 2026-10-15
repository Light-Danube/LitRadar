# LitBeacon 1.0 — active release checklist

Baseline main `4e2486d3` (merged PR #27 plus owner ignore update). Version stays **0.8.0**; no merge/tag/release authorization is implied.

- **Gate 1: closed.** [Archived feature inventory and closure evidence](archive/gate1/release-checklist-2026-10-15.md). Windows daily use and optional Narrator were accepted by the user; automated results remain separate.
- **Gate 2: complete for this candidate.** Read-only SQLite backup, new-destination restore, elected artifacts/checksums and legacy upgrade are tested. Actual [Ubuntu/Windows extracted setup-wheel recovery checks](https://github.com/Light-Danube/LitRadar/actions/runs/38744388702) passed at implementation head `a9c64fb2`; no personal data or services were used.
- **Gate 3: two explicit items remain.** Scheduler/optional Telegram duplicate-listener and disable/remove behavior; provider timeout/429/offline failure preservation. Daily-use acceptance and clean package installation are already recorded.
- Gate 3 current increment: [Telegram conflicts and safe listener diagnostics](GATE3-TELEGRAM-DIAGNOSTICS.md), with [operator troubleshooting](TELEGRAM-TROUBLESHOOTING.md). Scheduler and full provider-failure gates remain open.
- Gate 3 next increment: [safe provider failures and local-workspace preservation](GATE3-PROVIDER-FAILURES.md); [shared ignored log location](LOGGING.md). Candidate checks pending; scheduler verification remains open.
- Gates 4–6 remain governed by [ROADMAP](../ROADMAP.md), including focused safety checks and final release approval.

## This small Draft PR

1. Move completed Gate 1 audit/planning/validation history into `docs/archive/gate1/` and repair links; keep current setup/user/recovery instructions discoverable.
2. Close the earliest remaining gap vertically: add an installed-wheel backup/new-destination restore round-trip to existing package smoke, using only disposable synthetic data and elected artifacts.
3. Record actual candidate suite and Ubuntu/Windows results. Do not infer a package pass from source tests.

The recovery implementation remains bounded; no new subsystem, destructive migrations, personal database access, version bump or automatic merge. Gate 3 has more unchecked roadmap entries, but the final Gate 2 package evidence comes first. Next small PR: handle optional Telegram `getUpdates` HTTP 409 as a specific conflict and exit safely instead of retrying forever; use fake-API tests, preserve transient retries, Ctrl+C and stored offsets. Scheduler disable/remove and provider-failure workspace checks remain separate Gate 3 work.

## Candidate validation — 2026-10-15

- Linux Python 3.12: `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra` — **518 passed, 0 failed, 0 skipped**; one existing Starlette deprecation warning.
- `npm ci --prefix tests/web --ignore-scripts` (shared scratch cache), then `npm test --prefix tests/web` — **38 passed, 0 failed, 0 skipped**.
- `python -m pip wheel --no-deps --no-build-isolation --wheel-dir work/wheels .`; `python -m scripts.build_user_bundle ... --output-dir work/bundles`; extract ZIP, create fresh venv, install extracted wheel `[web]` plus smoke-only `httpx`, execute `scripts/built_wheel_smoke.py` from outside checkout — **passed on Linux**, including recovery CLI, exact durable table/history/tombstone comparison, elected files/checksums, integrity and no overwrite. FTS-derived tables are excluded from row comparison; legacy upgrade is covered by source tests.
- Documentation link/anchor scan: **221 targets resolved**; `python -m py_compile scripts/built_wheel_smoke.py` and `git diff --check` passed.
- Actual [Ubuntu/Windows installed-wheel CI](https://github.com/Light-Danube/LitRadar/actions/runs/38744388702) **succeeded** at implementation head `a9c64fb2`. Both job logs report the recovery round-trip and general CLI/assets/web/edit/restart smoke passed; reviewable setup ZIP artifacts uploaded. This closes Gate 2 package evidence. Final head `430ffcf0` had 20/20 successful checks before PR #26 was merged. This is not release approval.
