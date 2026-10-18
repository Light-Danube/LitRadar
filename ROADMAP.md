# LitBeacon — Local-Only v1.0 Release Roadmap

**Goal:** ship a dependable, maintainable, local-first **LitBeacon 1.0** for one researcher on their own computer. This is a **scope-freeze and release plan**, not a request to add another subsystem. The published release remains **0.8.0**; the **1.0.0 candidate** is merged into source `main` but is not a published release.

**Product boundary:** Python/SQLite is the source of truth. Web UI is bound to localhost; CLI, Textual TUI and the optional Telegram bot are existing interfaces. Existing paper libraries, research evidence, notes, tags, IDs, histories, offline PDFs and scheduler configuration must survive updates. Literature-provider searches require network access; the saved library and local workflows do not. Optional external LLM inference requires explicit opt-in. No account, hosted backend, public API or mandatory cloud component is in scope.

**Current baseline:** existing web/CLI/TUI/Telegram workflows, citation graph, annotations and recovery, venue-scoped search, evidence worksheets and local Research workspace are already implemented or documented in main. The user's 2026-10-14 web visual acceptance is not a substitute for packaging or Windows release tests. Existing v0.8.x implementation and historical test notes were moved to [the archived roadmap](docs/archive/ROADMAP-pre-v1-scope-freeze-2026-10-15.md). Consult CHANGELOG.md and CODEX-HANDOFF.md for detailed delivery history.

## Rules for the finish line

- **No major new feature work before 1.0.** Fix defects, data loss risks, packaging, local usability, installation, recovery and documentation.
- **No version bump just because a checkbox is checked.** Build, verify, and explicitly approve the release candidate first.
- **Keep all existing user data and compatibility paths.** Database schema changes must be additive/migrated and tested with disposable legacy fixtures; never erase or migrate the real local library for a test.
- **Network-dependent extras must fail gracefully.** Offline library access must work without provider, Telegram, embeddings or LLM services.
- **Use explicit evidence.** Mark each gate complete only with exact test command/results or an identified manual smoke-test record. Do not infer a Windows/browser/CI pass from Linux/jsdom tests.

## Gate 1 — Stabilize the current feature set (P0): complete

- [x] Feature inventory, regression checks and reproduced blockers closed through merged PRs #21–25. [Archived audit and closure evidence](docs/archive/gate1/release-checklist-2026-10-15.md), including actual Ubuntu/Windows setup ZIP checks, remain available.
- [x] Windows daily use and optional Narrator accepted by the user on 2026-10-15; no formal accessibility certification or unprovided platform observations are inferred.

Reopen for a reproduced workflow/data-loss defect. Live venue access remains cloud-environment-limited (proxy 403); user-reported CLI success is separate evidence. Active setup, recovery and operational guides remain current; completed planning and validation records are indexed in the [Gate 1 archive](docs/archive/gate1/README.md). Feature stability does not authorize a release/version bump.

## Gate 2 — Local data integrity and recovery (P0): complete for this candidate

- [x] Provide a documented **consistent SQLite backup** using SQLite's backup API and a read-only source without source migrations; committed active-WAL snapshot tested.
- [x] Implement bounded `library-backup`/`library-restore`, explicitly elected Research/offline roots, manifest/SHA-256 and exclusions. Artifact inclusion requires an explicit stopped-writers acknowledgment. [Instructions and limits](docs/USER-GUIDE.md#consistent-local-backup-and-restore-unreleased).
- [x] Demonstrate restore into a **new, disposable destination**, retaining all table data: notes/tags/status/IDs, citations/feedback, annotation/evidence histories/tombstones, preset tombstones and elected files. Corruption/missing/duplicate/path/schema/failure-cleanup checks execute on synthetic fixtures.
- [x] Restore an additive older LitRadar schema and upgrade twice, retaining existing fields, identities, metadata and histories. Compatibility identifiers remain unchanged.

**Done when:** automated tests verify backup, restore and upgrade without contacting services or touching personal data; USER-GUIDE documents restore steps and exclusions.

Source recovery and additive legacy upgrade are implemented and covered by synthetic tests. Actual [Ubuntu/Windows extracted setup-wheel recovery checks](https://github.com/Light-Danube/LitRadar/actions/runs/38744388702) succeeded at implementation head `a9c64fb2`, closing the package evidence gap through `scripts/built_wheel_smoke.py`. [Current candidate evidence](docs/LOCAL-1.0-RELEASE-CHECKLIST.md) records executed results and pending CI separately. No personal data or live services are used.

## Gate 3 — Windows-first install, launch and normal use (P0): complete for this candidate

- [x] Clean Windows Python 3.12 installed-wheel smoke verifies CLI, bundled assets and local edit/restart persistence; the setup ZIP follows the same CI path. [Actual runs and limits](docs/WINDOWS-WORKSPACE-SMOKE.md).
- [x] Windows daily use accepted by the user on 2026-10-15; detailed task/platform versions were not supplied. Synthetic API/DOM/native Chrome checks remain the separate automated evidence; this is not an invented per-task manual smoke transcript.
- [x] Stable scheduler task names/IgnoreNew, repeated install/status/per-job and all removal, explicit disabled guards/failures and selected paths verified by Windows fake/native unique-task checks. Optional Telegram duplicate-polling conflicts stop on 409; prompt idle/menu/retry Ctrl+C and normal offline use require no live Telegram credentials. [Lifecycle evidence and limits](docs/GATE3-LIFECYCLE.md). No cross-machine ownership lock or timed live delivery is claimed.

- [x] Synthetic 403/404/429/503/timeout/offline provider failures preserve stored library/evidence state and partial success; subsequent local workspace read/edit/export/reopen works. Actual Windows targeted checks succeeded at `3dfe583e`. [Evidence and limits](docs/GATE3-PROVIDER-FAILURES.md); no live provider availability claim.

Gate 3 is complete for the bounded candidate: actual Windows 37-test lifecycle/interface evidence at `845a6255` and native/fault-injection PowerShell checks at `6ed0fc8d`, with unchanged runtime code between them. [Closure record](docs/GATE3-LIFECYCLE.md) separates synthetic/native registration from user-reported daily use and live/timed behavior. Final documentation-head checks are tracked in PR #29; reopen for a reproduced normal-use/data-loss defect. Release/version approval remains Gate 6.

## Gate 4 — Safe local operating boundary (P0): complete for the bounded candidate

- [x] Verify web binds only to 127.0.0.1 by default and is not represented as suitable for public/LAN exposure; no authentication/server deployment is introduced for 1.0. [Local launch checks and limits](docs/GATE4-LOCAL-BOUNDARY.md); Linux verification only, hosted Actions deferred because of the account billing blocker by user instruction.
- [x] Verify path traversal, symlink, file-upload and export safeguards with synthetic fixtures; imports and restores must never follow arbitrary untrusted paths. [Research result/download checks](docs/GATE4-RESEARCH-PATHS.md) and [upload/restore acceptance](docs/GATE4-IMPORT-RESTORE-PATHS.md) provide bounded local evidence, including outside-fixture preservation and failure cleanup. Hosted Actions/native Windows remain deferred; these checks do not claim race-proofing against another local process or a complete security audit.
- [x] Verify SQLite changes, retryable failures, bad metadata and duplicate external identifiers do not discard manual notes/status/tags or overwrite research evidence. [Disposable integrity checks and canonical-identity fixes](docs/GATE4-INTEGRITY-CLOSURE.md) include reopen, rollback and real SQLite lock/retry evidence.
- [x] Document clearly which operations use the network: OpenAlex, Semantic Scholar, arXiv, optional Unpaywall, Telegram and explicitly invoked cloud LLMs. [Network-use reference](docs/NETWORK-USE.md); legacy model loading now uses local/cached weights only, with keyword fallback. No mandatory telemetry sender was found in the scoped application review.

**Done when:** existing targeted security/regression tests pass and limitations are described accurately (not labeled as a complete security audit).

[Gate 4 closure](docs/GATE4-INTEGRITY-CLOSURE.md) records bounded Linux evidence and limits. Hosted Actions/native Windows re-verification remain deferred by user instruction; this does not approve a release/version bump or certify hostile-local-process/parser security. Proceed vertically to Gate 5.

## Gate 5 — Local usability and accessibility evidence (P1; complete for this candidate)

- [x] Review core keyboard workflows in the existing web UI and Textual TUI in both English and Ukrainian: navigation, focus, close/cancel, scrolling, error messages, and keeping unsaved drafts. [Annotation editor focus](docs/GATE5-KEYBOARD-FOCUS.md), [TUI modal/error checks](docs/GATE5-TUI-KEYBOARD.md) and the [Research DOM journey](docs/GATE5-RESEARCH-KEYBOARD.md) are bounded slices with stated platform limits.
- [x] User-reported Windows/Narrator acceptance recorded on 2026-10-15; Narrator is optional for this release. The [detailed audit procedure](docs/TUI-ACCESSIBILITY-AUDIT.md) remains available for optional broader testing; no WCAG/screen-reader certification is claimed.
- [x] Ordinary-user Research use accepted by the user on 2026-10-18, including the venue/evidence/export path covered by EN/UK synthetic DOM checks. This is user-reported acceptance, without an independently observed task transcript or native-browser test.

**Done when:** keyboard/smoke evidence and unresolved limitations are documented. A full accessibility certification, new UI design, new localization languages and TUI menu overhaul are **not** release gates.

Gate 5 is complete for this bounded local candidate. Gather further usability feedback after the initial release as separate, specific follow-ups. This does not approve a version bump or release.

## Gate 6 — Versioning, documentation and release artifact (P0)

- [ ] Make VERSION, pyproject.toml, CLI/TUI/Telegram/Web visible version strings, package metadata, changelog and release tag consistent **after** candidate verification. The [Draft 1.0.0 candidate](docs/GATE6-1.0-CANDIDATE.md) aligns existing version surfaces; tag and release approval remain pending.
- [ ] Build and install the distribution in a clean environment; run a smoke test against packaged static assets. Verify release ZIP/wheel contain no .env, local SQLite, PDFs, credentials, logs or source caches. The [1.0.0 candidate](docs/GATE6-1.0-CANDIDATE.md) passed a fresh Linux package install and inventory. The user's fresh Windows source-ZIP attempt exposed an older-Python/overbroad-installer blocker; [Draft PR #40](docs/WINDOWS-SOURCE-ZIP.md) narrows setup and requires a native retest. macOS and same-commit required CI remain pending.
- [ ] Keep README concise. Publish a working quick start, docs/USER-GUIDE.md, migration and backup/restore guide, optional component instructions, known limitations and a reproducible upgrade path from v0.8.0.
- [x] Create a **1.0 release-candidate checklist** with check names, executed results, platform and known limitations. [Historical 0.8.0 rehearsal](docs/GATE6-RELEASE-CANDIDATE.md) and [current 1.0.0 candidate](docs/GATE6-1.0-CANDIDATE.md).
- [ ] Review the final-version draft PR; merge/tag/release only with explicit user approval.

**Done when:** the same candidate commit passes required CI and Windows smoke, its built artifact installs, and release notes describe exactly what has and has not been verified.

## Recommended sequence (small draft PRs)

| Step | Scope | Expected output |
| --- | --- | --- |
| 1 | Freeze inventory + failures (Gate 1) | A minimal release checklist; reproducible defect list |
| 2 | Backup, restore, legacy upgrade (Gate 2) | Tested recovery commands and documentation |
| 3 | Windows/packaging fixes (Gates 3 and 6) | Clean-install smoke and consistent bundled assets |
| 4 | Safety + practical accessibility (Gates 4 and 5) | Focused regression fixes and honest limitations |
| 5 | Release candidate (Gate 6) | Verified RC, then explicit approval to tag 1.0.0 |

A PR should cover one step or a clearly bounded defect, not all gates at once. No date commitment is implied.

## Not required for v1.0 (remove from active roadmap)

- Named multi-project workspaces, advanced reading queues, citation-gap prediction, collaborative features, accounts and server synchronization.
- More provider integrations solely to increase source count; use existing OpenAlex venue IDs/ISSN and clear provenance first.
- New semantic clustering/model evaluation as a release blocker. The existing optional semantic feature remains explicitly experimental/off by default.
- Zotero or other reference-manager sync; automated novelty/scientific-quality scoring; unverified journal-indexing certification.
- Public web/VPS hosting, server authentication stack, remote scheduler, cloud database or mobile clients.
- Docker production/VPS optimization or a Codex-agent devcontainer. Existing Compose/test runner may remain available, but Docker is **optional** for a standard local Windows 1.0 install.
- New graph framework, large UI redesign, additional translations or a broad architecture rewrite.

After 1.0, capture **specific user-validated requests** as separate issues with acceptance criteria. Do not re-add a generic “later” bucket to the release roadmap.
