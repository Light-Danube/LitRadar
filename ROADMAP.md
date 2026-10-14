# LitBeacon — Local-Only v1.0 Release Roadmap

**Goal:** ship a dependable, maintainable, local-first **LitBeacon 1.0** for one researcher on their own computer. This is a **scope-freeze and release plan**, not a request to add another subsystem. Official current version remains **0.8.0** until release gates are satisfied.

**Product boundary:** Python/SQLite is the source of truth. Web UI is bound to localhost; CLI, Textual TUI and the optional Telegram bot are existing interfaces. Existing paper libraries, research evidence, notes, tags, IDs, histories, offline PDFs and scheduler configuration must survive updates. Literature-provider searches require network access; the saved library and local workflows do not. Optional external LLM inference requires explicit opt-in. No account, hosted backend, public API or mandatory cloud component is in scope.

**Current baseline:** existing web/CLI/TUI/Telegram workflows, citation graph, annotations and recovery, venue-scoped search, evidence worksheets and local Research workspace are already implemented or documented in main. The user's 2026-10-14 web visual acceptance is not a substitute for packaging or Windows release tests. Existing v0.8.x implementation and historical test notes were moved to [the archived roadmap](docs/archive/ROADMAP-pre-v1-scope-freeze-2026-10-15.md). Consult CHANGELOG.md and CODEX-HANDOFF.md for detailed delivery history.

## Rules for the finish line

- **No major new feature work before 1.0.** Fix defects, data loss risks, packaging, local usability, installation, recovery and documentation.
- **No version bump just because a checkbox is checked.** Build, verify, and explicitly approve the release candidate first.
- **Keep all existing user data and compatibility paths.** Database schema changes must be additive/migrated and tested with disposable legacy fixtures; never erase or migrate the real local library for a test.
- **Network-dependent extras must fail gracefully.** Offline library access must work without provider, Telegram, embeddings or LLM services.
- **Use explicit evidence.** Mark each gate complete only with exact test command/results or an identified manual smoke-test record. Do not infer a Windows/browser/CI pass from Linux/jsdom tests.

## Gate 1 — Stabilize the current feature set (P0)

- [x] Record an accurate feature inventory and list of known defects from current main and open PRs. [Gate 1 audit](docs/LOCAL-1.0-RELEASE-CHECKLIST.md): baseline `b8b42ff4`, no open PR backlog, reproduced installed-wheel CLI failure. Implemented, user-accepted and externally unverified behavior are separated.
- [x] Run the full Python and JS suites on the candidate, fix reproducible failures and explain profile-dependent CI skips. [Current executed evidence and candidate checks](docs/LOCAL-1.0-RELEASE-CHECKLIST.md).
- [x] Verify **Research** venue search/evidence, original five sections, EN/UK and draft persistence with synthetic API/DOM/native Windows workflows; page load/preset selection makes no provider/LLM POST.

[Venue verification](docs/research/venue-verification.md) adds CLI/API checks through the mocked HTTP transport boundary: identity/year validation, cache/persistence and failed-request preservation. Combined checks: **447 Python / 38 JS passed, 0 failed, 0 skipped**. An explicit public live lookup failed at the cloud proxy tunnel (403); further live-provider/browser verification is pending and user-reported success remains separate.

**Done when:** CI is green on the candidate commit, a compact feature/regression checklist exists, and no known data-loss or workflow-blocking defect remains.

**Gate 1 closure:** the prior defect/verification PRs #22–24 are merged, the wheel blocker is fixed, and current baseline CI includes successful Ubuntu/Windows installed-wheel smoke. The package-setup candidate adds a wheel-only setup ZIP, fresh complete regressions and extracted-package CI. Gate 1 is accepted when this candidate's required checks are green; reopen it for a reproduced workflow/data-loss defect. This is feature-stability completion, not 1.0 release approval. Live venue access remains environment-limited (proxy 403), with user-reported CLI success kept separate.

On 2026-10-15 the user confirmed Windows daily use and Narrator work okay and accepted them as “yes”. Record this as **user-reported acceptance**; Narrator is optional for this release, and no detailed screen-reader certification or unprovided platform/version observations are inferred.

## Gate 2 — Local data integrity and recovery (P0)

- [x] Provide a documented **consistent SQLite backup** using SQLite's backup API and a read-only source without source migrations; committed active-WAL snapshot tested.
- [x] Implement bounded `library-backup`/`library-restore`, explicitly elected Research/offline roots, manifest/SHA-256 and exclusions. Artifact inclusion requires an explicit stopped-writers acknowledgment. [Instructions and limits](docs/USER-GUIDE.md#consistent-local-backup-and-restore-unreleased).
- [x] Demonstrate restore into a **new, disposable destination**, retaining all table data: notes/tags/status/IDs, citations/feedback, annotation/evidence histories/tombstones, preset tombstones and elected files. Corruption/missing/duplicate/path/schema/failure-cleanup checks execute on synthetic fixtures.
- [x] Restore an additive older LitRadar schema and upgrade twice, retaining existing fields, identities, metadata and histories. Compatibility identifiers remain unchanged.

**Done when:** automated tests verify backup, restore and upgrade without contacting services or touching personal data; USER-GUIDE documents restore steps and exclusions.

Implementation evidence: Linux Python 3.12.14 recovery **49 passed / 0 failed / 0 skipped**; full recovery branch **479 Python / 38 JS passed, 0 failed, 0 skipped**. A disposable integration of the separate packaging/recovery/venue changes passed **501 Python tests** and installed-wheel recovery/web smoke. Gate 2 source checks are implemented; final recovery-head CI and Windows recovery remain to be observed. This does not close Gate 1 or authorize a release/version bump.

## Gate 3 — Windows-first install, launch and normal use (P0)

- [x] Clean Windows Python 3.12 installed-wheel smoke verifies CLI, bundled assets and local edit/restart persistence; the setup ZIP follows the same CI path. [Actual runs and limits](docs/WINDOWS-WORKSPACE-SMOKE.md).
- [x] Windows daily use accepted by the user on 2026-10-15; detailed task/platform versions were not supplied. Synthetic API/DOM/native Chrome checks remain the separate automated evidence; this is not an invented per-task manual smoke transcript.
- [ ] Verify jobs and optional Telegram do not start duplicate listeners on the same token; disable/remove schedule flows work. Require no Telegram credentials for normal offline use.
- [ ] Confirm source APIs can fail (timeout, 429, unavailable internet) without losing stored papers or making the local UI unusable.

**Done when:** exact Windows environment and reproducible manual/automated results are recorded in docs/WINDOWS-WORKSPACE-SMOKE.md or a release-check file. Linux-only checks do not satisfy this gate.

## Gate 4 — Safe local operating boundary (P0)

- [ ] Verify web binds only to 127.0.0.1 by default and is not represented as suitable for public/LAN exposure; no authentication/server deployment is introduced for 1.0.
- [ ] Verify path traversal, symlink, file-upload and export safeguards with synthetic fixtures; imports and restores must never follow arbitrary untrusted paths.
- [ ] Verify SQLite changes, retryable failures, bad metadata and duplicate external identifiers do not discard manual notes/status/tags or overwrite research evidence.
- [ ] Document clearly which operations use the network: OpenAlex, Semantic Scholar, arXiv, optional Unpaywall, Telegram and explicitly invoked cloud LLMs. No hidden model downloads or mandatory telemetry.

**Done when:** existing targeted security/regression tests pass and limitations are described accurately (not labeled as a complete security audit).

## Gate 5 — Local usability and accessibility evidence (P1; no scope expansion)

- [ ] Review core keyboard workflows in the existing web UI and Textual TUI in both English and Ukrainian: navigation, focus, close/cancel, scrolling, error messages, and keeping unsaved drafts.
- [x] User-reported Windows/Narrator acceptance recorded on 2026-10-15; Narrator is optional for this release. The [detailed audit procedure](docs/TUI-ACCESSIBILITY-AUDIT.md) remains available for optional broader testing; no WCAG/screen-reader certification is claimed.
- [ ] Confirm an ordinary user can locate venue search, open/save an evidence worksheet and export it, without having to learn the CLI.

**Done when:** keyboard/smoke evidence and unresolved limitations are documented. A full accessibility certification, new UI design, new localization languages and TUI menu overhaul are **not** release gates.

## Gate 6 — Versioning, documentation and release artifact (P0)

- [ ] Make VERSION, pyproject.toml, CLI/TUI/Telegram/Web visible version strings, package metadata, changelog and release tag consistent **after** candidate verification.
- [ ] Build and install the distribution in a clean environment; run a smoke test against packaged static assets. Verify release ZIP/wheel contain no .env, local SQLite, PDFs, credentials, logs or source caches.
- [ ] Keep README concise. Publish a working quick start, docs/USER-GUIDE.md, migration and backup/restore guide, optional component instructions, known limitations and a reproducible upgrade path from v0.8.0.
- [ ] Create a **1.0 release-candidate checklist** with check names, executed results, platform and known limitations. Review the draft PR; merge/tag/release only with explicit user approval.

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
