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
- [ ] Run the full Python and JS suites on the release candidate. Fix all reproducible failures. Explain every expected skip; no unexplained failures/skips in required CI jobs.
- [ ] Verify **Research** venue search and evidence worksheets, original five web sections, EN/UK switching and draft persistence with synthetic data. No automatic provider/LLM request from page load or preset selection.

[Venue verification](docs/research/venue-verification.md) adds CLI/API checks through the mocked HTTP transport boundary: identity/year validation, cache/persistence and failed-request preservation. Combined checks: **447 Python / 38 JS passed, 0 failed, 0 skipped**. An explicit public live lookup failed at the cloud proxy tunnel (403); further live-provider/browser verification is pending and user-reported success remains separate.

**Done when:** CI is green on the candidate commit, a compact feature/regression checklist exists, and no known data-loss or workflow-blocking defect remains.

Audit evidence: Linux combined suite **430 Python / 38 JS passed, 0 failed, 0 skipped**. Actual baseline Windows API/DOM/native Chrome checks succeeded, but clean built-artifact Windows installation and Narrator remain open. Gate 1 is not closed: final candidate CI remains open. The focused packaging fix resolves the reproduced import/default-path failure in local Linux installed-artifact smoke; actual Windows wheel CI is still unverified. The bounded SQLite backup/new-destination restore PR remains the next Gate 2 step; no version bump is included.

## Gate 2 — Local data integrity and recovery (P0)

- [ ] Provide a documented **consistent SQLite backup** using SQLite's backup API or another safe, tested snapshot mechanism (not raw copying of an open database).
- [ ] Define and implement a bounded local backup/restore workflow covering the SQLite library and durable research/offline artifacts that the user elects to include. Record a manifest/checksums and what is excluded (for example, .env credentials); never silently overwrite existing files.
- [ ] Demonstrate restore into a **new, disposable destination**, including notes, tags, annotation/evidence history, citation relationships and saved research bundles. Include corruption/missing-file/duplicate-path failure tests.
- [ ] Verify an upgrade from a synthetic older LitRadar database, preserving legacy LITRADAR_* names, paper identities, user edits and metadata.

**Done when:** automated tests verify backup, restore and upgrade without contacting services or touching personal data; USER-GUIDE documents restore steps and exclusions.

## Gate 3 — Windows-first install, launch and normal use (P0)

- [ ] Install a **built release artifact** (wheel and/or release ZIP, as actually distributed) into a clean Windows Python environment supported by pyproject.toml (Python 3.11+). Verify bundled HTML/JS/CSS/icons and package imports.
- [ ] Execute a documented Windows smoke checklist: setup/update script, CLI help, TUI open/search, browser open on 127.0.0.1, select/edit paper, local annotations/evidence, graph, BibTeX/Markdown/CSV export, restart and persistence. Use a **synthetic test library**.
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
- [ ] Run the planned **Windows Terminal + Narrator** manual TUI check using docs/TUI-ACCESSIBILITY-AUDIT.md and the synthetic fixture. Record actual observations and any workarounds. Do not claim WCAG/screen-reader certification; serious blockers to basic operation must be fixed or clearly declared unsupported before release.
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
