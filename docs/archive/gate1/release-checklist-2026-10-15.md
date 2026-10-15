# Archived Gate 1 closure record

Gate 1 closed at merged PR #25, candidate `9e5fe8f5`, with actual green CI. This dated record preserves its evidence and historical pending wording; current gates are in [the active checklist](../../LOCAL-1.0-RELEASE-CHECKLIST.md).

# Local-only LitBeacon 1.0 — release checklist

Updated 2026-10-15; package-setup baseline main [`1d1a2ca6`](https://github.com/Light-Danube/LitRadar/commit/1d1a2ca67d4d63c88434159e61d22acb8e88f418). Application version remains **0.8.0**. Feature development is frozen; gate completion does not authorize merge, version bump, tag or release.

## Gate 1 — completion record

- [x] Inventory current main and reconcile PRs: venue verification [#22](https://github.com/Light-Danube/LitRadar/pull/22), packaging [#23](https://github.com/Light-Danube/LitRadar/pull/23) and recovery [#24](https://github.com/Light-Danube/LitRadar/pull/24) are merged; no earlier open PR/issue backlog was returned.
- [x] Remove reproduced wheel blocker: config/version/default assets are bundled; writable data stays outside site-packages. Actual clean Ubuntu/Windows installed-wheel checks succeeded.
- [x] Exercise existing Research and original five sections, EN/UK, draft retention, guarded evidence, cache/dedup, imports/recovery and graph workflows with synthetic fixtures. Page load/preset selection requires no provider/LLM POST.
- [x] Record Windows daily-use and Narrator acceptance: user said they work okay on 2026-10-15 and requested “yes”. This is user-reported evidence, with no supplied platform versions or per-task transcript. Narrator is optional; no certification is inferred.
- [x] Execute candidate full regressions and extracted-package smoke: **518 Python / 38 JS passed, 0 failed, 0 skipped**; clean Linux extracted-wheel install/smoke passed. The Draft PR's actual final-head checks supply the required CI closure evidence.

**Gate 1 is complete for the tested feature-stability candidate once its actual required CI checks are green.** No current reproducible feature/workflow blocker was identified. Reopen for a reproduced workflow/data-loss defect. Later release gates remain separate.

## Frozen regression inventory

| Existing workflow | Implementation / exercised tests | Evidence boundary |
| --- | --- | --- |
| Overview, Literature, Graph, Clusters, Jobs, Research | workspace API tests; shell/workflows/research DOM suites; [48 preservation contracts](ux-research/feature-parity.md) | Synthetic data; native Windows subset |
| Notes/tags/status, feedback, exports and offline bundles | storage, sorting/tags, bibliography/offline and CLI tests | No personal library/PDF access |
| Citation direction/provenance/filtering, gestures and exports | mixed-provider Python and graph JS suites | No scientific-quality/novelty claim |
| EN/UK web/TUI, themes, drafts and worker recovery | shell/research/UI workflow/localization suites | User acceptance separate from automation |
| Annotation imports/revisions, soft delete/undo, note restoration | annotation adapter/recovery suites | Optional parsers explicit; providers mocked |
| Venue identities/year filters, presets, evidence, immutable results | venue transport/API/CLI/files/evidence/preset suites | Explicit actions; manual fields/history preserved |
| SQLite backup/restore and additive legacy upgrade | library recovery/migration suites | Active WAL, checksums, unsafe paths, all-table/history/tombstone preservation |
| Optional semantic exploration/LLM/Telegram/jobs | semantic, annotation consent, Telegram/schedule suites | Off-default models; services/scheduler mocked |

## Executed verification

Candidate local Linux/Python 3.12.14: `python -m pytest -q -ra` **518 passed / 0 failed / 0 skipped**, 25.37s, one existing Starlette deprecation warning. After pinned `npm ci --prefix tests/web --ignore-scripts`, `npm test --prefix tests/web`: **38 passed / 0 failed / 0 skipped**. Built/validated the version-matched setup ZIP, extracted it, installed its `[web]` wheel plus smoke-only httpx into a fresh venv using declared dependencies, and executed `scripts/built_wheel_smoke.py` outside the checkout: CLI/version/init/fixture/list, all static assets, synthetic edit/restart/custom-DB persistence and non-overwriting defaults passed. Changed Python syntax, documentation links and `git diff --check` passed. No personal data/provider/model access.

**Observed setup ZIP CI:** [Ubuntu and Windows run](https://github.com/Light-Danube/LitRadar/actions/runs/38657414211) at code head `3cb012b1` succeeded, including clean extraction/dependency installation, runtime smoke and uploaded two-file review artifacts. This is actual Windows package evidence, separate from the user-reported daily-use/Narrator acceptance. [Draft PR #25 checks](https://github.com/Light-Danube/LitRadar/pull/25/checks) record the final candidate result, including any later documentation-only head. Baseline evidence follows:

| Evidence | Observed result |
| --- | --- |
| [Baseline main Python/JS CI](https://github.com/Light-Danube/LitRadar/actions/runs/38656486338) | Python 3.11/3.12 core 398 passed / 47 skips; UI 426 / 19; web 473 / 28; Node 38 passed / 0 failures/skips. Skips are absent optional browser/Textual dependencies, not unexplained failures. |
| [Baseline clean wheel install](https://github.com/Light-Danube/LitRadar/actions/runs/38656486258) | Ubuntu and Windows succeeded: CLI/version/defaults/static assets, synthetic web edit/restart and custom database outside the checkout. |
| [Windows recovery/API/DOM/native Chrome](https://github.com/Light-Danube/LitRadar/actions/runs/38651164554) | Recovery+legacy upgrade 49 passed / 1 case-insensitive-filesystem skip; API 129 / 1 POSIX-permission skip; Node 38/0/0; four sandboxed EN/UK desktop/narrow scenarios passed. |
| [Baseline isolated Docker](https://github.com/Light-Danube/LitRadar/actions/runs/38656486269) | 470 passed / 31 explained optional Textual/parser/Node skips. |
| Live venue lookup | Explicit adapter probe encountered cloud proxy tunnel 403 before OpenAlex. [Procedure and evidence](research/venue-verification.md); user-reported CLI success stays separate. Further live-provider verification is an environment limitation, not a hidden automated pass or a known universal provider outage. |
| Human acceptance | WebUI accepted 2026-10-14; Windows daily use and optional Narrator accepted 2026-10-15. Broader reader/participant studies and certification are not implied. |

The original Gate 1 wheel-import failure and early Docker/PR-check failures are historical: merged fixes and later executed runs supersede them. New failures must be assessed at their actual commit, not inferred from stale handoff text.

## Small package setup

[Setup and upgrades](../../PACKAGE-SETUP.md): `LitBeacon-<version>-setup.zip` contains **only the runtime wheel and SETUP.txt**. Users need Python 3.11+ and internet for pip dependencies; they do not need a source checkout, Node, Docker, tests, legacy docs, models or cloud LLM SDKs. Default `[web]` keeps optional components separate. Existing source launchers remain available.

The builder verifies runtime inventory, version/tag agreement and excludes local/development data; existing archives are never overwritten. CI installs from the extracted ZIP on Ubuntu/Windows and uploads review artifacts. Future release attachment runs only after an owner publishes a matching release and its smoke passes; this PR does not publish one. GitHub's automatic source archives remain available for developers.

## Remaining 1.0 release gates

- [x] Gate 2 source recovery/legacy-upgrade checks implemented and exercised with synthetic data; profiles/digest/scheduler/credential preservation is documented separately. No personal-library drill was performed.
- [x] Windows installed-wheel/API/DOM/native Chrome evidence and user daily-use acceptance recorded. Detailed manual environment/task versions were not supplied.
- [ ] Confirm real scheduler duplicate-listener/disable/remove behavior with synthetic configuration, without using personal Telegram tokens.
- [ ] Complete the focused Gate 4 local-boundary/elected-artifact safety evidence and network-operation documentation; no complete-security-audit claim.
- [ ] Verify the final release candidate and its actual wheel/setup ZIP, migration/upgrade instructions and exclusions. Gate 6 still requires explicit version/tag/release approval.

Narrator is optional and accepted by the user; a full cross-reader audit or new neural-model evaluation is not a new Gate 1 blocker. Keep experimental limitations and the blocked live-provider probe explicit.
