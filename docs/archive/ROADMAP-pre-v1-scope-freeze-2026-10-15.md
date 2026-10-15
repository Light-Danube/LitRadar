# Archived roadmap (before local-only v1.0 scope freeze)

Historical v0.8.x changes, existing feature notes and abandoned/future ideas. For the active release gates, see [ROADMAP.md](../../ROADMAP.md).

---

# LitBeacon Research Workspace — Roadmap

## Unreleased — Ukrainian Textual TUI and job crash fixes

- [x] Extend English/Ukrainian localization to the existing Textual TUI, with runtime language selection, translated app controls/help/details/activity and preserved technical identifiers and paper content.
- [x] Fix jobs worker UI dispatch, busy/error/close handling and immediate filtering by newly saved tags; run synthetic keyboard/worker regressions.
- [x] Prepare an [existing-feature-only menu optimization draft](gate1/TUI-MENU-DRAFT.md), plus targeted keyboard scrolling/focus and compact-toolbar fixes.
- [ ] Complete the full accessibility audit with assistive technology: user-selected **Windows Terminal + Narrator** remains pending. [Executed audit, limits and safe fixture procedure](../TUI-ACCESSIBILITY-AUDIT.md).

Validation: **430 Python passed / 0 failed / 0 skipped; 6 Node test files passed / 0 failed / 0 skipped**. The TUI subset passed 29 tests; ANSI PTY and disposable audit-fixture smoke checks passed separately. Textual 1.0.0 tested; UI dependency minimum is now 1.0. Remote CI and real Narrator output are unverified. Release version remains 0.8.0; no CLI/web feature expansion or README changes in this patch.

## Unreleased — browser research workspace

- Add a sixth Research section for explicit venue-scoped search and editing the existing evidence worksheets, with EN/UK, preserved drafts and library filters for to-read/new/all. Keep the prior five sections and Alt+1–5; Alt+6 opens Research.
- Add editable topic/venue shortcut cards with local icons, conservative unresolved defaults and revision-guarded changes. Card selection fills the form without a provider request; concrete identity resolution remains explicit.
- Save search pages, worksheet snapshots and Markdown/CSV exports to unique local `data/research/<identifier>/` bundles; generated IDs or validated user names never overwrite existing results. Existing SQLite library and personal notes remain authoritative/intact.
- User reports live CLI API retrieval succeeds locally (2026-10-14); this supersedes an assumption of universal inaccessibility, while historical cloud 403 probes remain separate evidence. No automatic inference or indexing/novelty certification.
- Local checks: **405 Python passed / 0 failed / 0 skipped; 6 Node test files passed / 0 failed / 0 skipped**. Browser rendering blocked before launch by SUID sandbox configuration; Windows/remote CI results not claimed.
- [Browser workflow, storage and verification](../research/web-workspace.md) · [quick-topic design](../research/quick-venues.md). Release version remains 0.8.0.

## Unreleased — compact documentation and CLI guidance

- Keep README as a compact overview/quick start, with detailed instructions in `docs/USER-GUIDE.md`; AGENTS now records this maintenance rule.
- Add discoverable `venue`/`evidence` help examples and a [Russian practical workflow](../research/cli-workflow-ru.md) explaining evidence quality, research use and remaining limits. No retrieval/storage behavior or release version changes. Validation: 298 Python passed / 0 failed / 0 skipped; 5 Node test files passed / 0 failed / 0 skipped; CLI help examples and Markdown links checked.

## Unreleased — venue discovery and evidence worksheet

A CLI-first vertical slice adds opt-in OpenAlex venue lookup and structured source/year search, separate from existing broad discovery. Concrete source IDs distinguish same-name venues. One bounded page is cached with all filters; source metadata, query URL and UTC retrieval time are retained separately from canonical papers. Provider metadata does not certify peer review or Scopus/WoS membership. Existing paper IDs, notes, tags, status, relations and scores survive enrichment; conflicting DOI/provider aliases fail atomically.

Human-editable evidence worksheets retain per-field provenance and revision history, independently of personal notes. Markdown/CSV exports include unknown evidence, venue observations and unverified gap candidates; no LLM calls occur. [Usage, bounds and recovery](../research/venue-discovery.md), [implementation contracts](gate1/research/implementation-plan.md), and [literature review](gate1/research/erc-context-novelty-matrix-2026.md).

Local validation: **298 Python tests passed / 0 failed / 0 skipped; 5 Node test files passed / 0 failed / 0 skipped**. [Executed checks and pending evidence](gate1/research/delivery-validation.md).

Browser venue-discovery controls remain planned; retrieved paper IDs are available in the existing Literature inbox. Release version stays 0.8.0. Live OpenAlex and Crossref requests failed at the proxy with `Tunnel connection failed: 403 Forbidden`; fixture tests do not verify live metadata or coverage. Windows, rendered-browser and neural-model evaluations are not claimed.

This roadmap separates implemented behavior from research ideas that still need validation. A feature is not considered complete merely because a UI element exists: it should have offline tests, an explicit limitation note where appropriate, and a workflow verified against the local library.

## Current: v0.8.0 — Local research workspace

- [x] Browser UI served locally by FastAPI/Uvicorn, without a Node runtime or external CDN.
- [x] Literature inbox with search/filter/sort, paper detail, and edits for workflow status, tags, and notes.
- [x] Bounded SVG exploration of citation and related-work edges already present in the SQLite database.
- [x] Lightweight exploratory clusters based on user tags, repeated venue, and shared title/abstract terms. Clearly labeled as heuristic, not semantic clusters.
- [x] Job controls in CLI, TUI (`J`), and Telegram for viewing, installing defaults, and removing scan/digest jobs independently.
- [x] Local-only server binding and route validation; no unauthenticated LAN/public deployment.
- [x] Updated README, tests, and compatibility-aware LitBeacon branding.

## v0.8.x — Research-map usability and annotations

- [x] Refine the shell identity around the supplied Telegram mascot, add a packaged local mark/favicon and accessible Beacon Blue palettes (unreleased; visual accepted by user on 2026-10-14).

- [x] Implement Phase 1 shared tokens, light/dark/system appearance and responsive shell with EN/UK and regression checks (unreleased; visual accepted by user on 2026-10-14). See [verification notes](gate1/ux-research/phase-1.md).
- [x] Current WebUI visual/functionality accepted by the user (2026-10-14); skip the additional cloud-browser gate as requested. No automated browser pass is claimed. Phase 2 navigation proposals remain separate future research.
- [x] Review and implement the [readability/UX design draft](gate1/ux-research/README.md), retain the [public-source competitor review](gate1/ux-research/live-review-2026-10-13.md) and user acceptance of the implemented redesign. No additional hands-on competitor or participant study is claimed. Preserve all 48 current web contracts; ship tokens/shell, library/detail, provenance, graph and secondary screens in separate reviewed increments.

- [x] Add graph pan/zoom, keyboard/click node selection, directional arrows/legend, relation/provider filters applied before bounded traversal, and merged edge provenance (unreleased).
- [x] Improve graph layout with deterministic BFS layers and separated labels; apply year-range/unknown-year filters before traversal; export the displayed graph to standalone SVG, GraphML and JSON (unreleased).
- [x] Add the provenance foundation: user/imported/extracted/generated supplemental annotations, recording timestamps and optional source references, research-note revisions, and explicit unknown provenance for legacy notes (unreleased).
- [x] Integrate bounded, repeat-safe JSON annotation import and stored-metadata extraction, opt-in suggestions from stored assessments/local reading prompts, review/edit with revision-conflict checks, and paginated research-note history UI (unreleased). Automatic entries record the adapter; manual origin labels remain declarations.
- [x] Extend annotation adapters to PDF/RIS/BibTeX and atomic multi-file uploads; add per-paper opt-in fresh LLM inference with provider/model choice, append-only history restoration and reversible annotation deletion (unreleased). See [limits, recovery behavior and tests](../V08-ANNOTATION-WORKFLOWS.md). Live provider calls remain unverified.
- [x] Add cursor-anchored wheel zoom, draggable graph nodes, Shift+arrow movement, locally saved node layouts/reset and layout-aware SVG export (unreleased).
- [x] Implement ephemeral semantic-similarity related edges and complete-link embedding clusters behind an OFF-default feature flag/local-only model dependency, with synthetic fixtures and an attributed shareable title corpus.
- [ ] Complete real neural-model quality evaluation on the [shareable corpus](../SEMANTIC-WORKSPACE.md); lexical controls have run, model/metadata access remains blocked.
- [x] Test graph direction, mixed OpenAlex/Semantic Scholar aliases, duplicates/self-edges, antiparallel citations, cycles, refresh and merged provenance with synthetic fixtures.
- [x] Add synthetic API and EN/UK DOM workflow smoke tests for inbox editing, clusters and graph navigation.
- [ ] Confirm the [Windows workflow](../WINDOWS-WORKSPACE-SMOKE.md) result on Windows; the same commands passed locally on Linux.
- [x] Add bounded node/label collision settling, fix native single-click selection and group exports in a keyboard-accessible menu. Keep zoom buttons for keyboard users.
- [x] Refine Web UI onboarding, semantic paper buttons/labels, skip link, Alt+1–5 / search / save shortcuts, empty/loading/error/retry states, visible focus and contrast (unreleased; no claim of a complete accessibility audit).
- [x] Add Ukrainian Web UI localization with externalized English/Ukrainian strings, a persisted language selector, localized statuses/help/actions, and Unicode workflow checks; preserve CLI/config identifiers (unreleased).
- [ ] Extend Ukrainian localization to Textual TUI and perform a full accessibility audit with assistive technology (localization and automated TUI checks complete; Windows Terminal + Narrator audit pending — see [audit evidence](../TUI-ACCESSIBILITY-AUDIT.md)).

## v0.9 — Research projects and reading workflow

- [ ] Named projects/collections with per-project seed papers, saved searches, and configurable digest settings.
- [ ] Reading queue actions such as prioritize, snooze, mark read, and add a review note from one workspace.
- [ ] Citation-gap review: identify papers repeatedly referenced in the current collection but not yet saved, with evidence shown for each suggestion.
- [ ] Import/export project snapshots and interoperability improvements for BibTeX/RIS; do not silently merge conflicting DOI identities.
- [ ] Optional semantic cluster evaluation: measure cohesion, stability, and user usefulness before presenting clusters as more than suggestions.

## v1.0 — Hardened local-first workspace

- [ ] Complete the migration guide from the LitRadar display name to LitBeacon while preserving database, configuration, CLI, and task compatibility.
- [ ] Decide whether a separate remote/server mode is warranted. Before remote use: implement authentication, origin/CSRF protections, secret isolation, database backup/restore, and a deployment model.
- [ ] Document recovery/backup procedures and provide a tested database backup command.
- [ ] Add a supported Windows smoke-test checklist and CI package-install test covering the built wheel and static web assets.

## Later / only if supported by use cases

- [ ] Optional reference-manager sync (for example Zotero), subject to API availability and non-destructive conflict handling.
- [ ] Optional collaborative workspace with explicit user accounts and permissions.
- [ ] Optional remote scheduler/worker for digests that must run while the user's PC is off; requires a deliberate database sync and secret-management design.
- [ ] A graph library such as Cytoscape.js only if native SVG no longer meets tested interaction/performance needs.

## Principles and release gates

1. Keep SQLite as the source of truth for local-first usage; use additive migrations.
2. Never imply that lexical overlap, citations, or clusters prove/disprove scientific novelty.
3. Keep API traffic bounded, cache provider results, and distinguish provider failure from an empty result.
4. Optional heavy dependencies (embeddings, LLMs, graph visualization libraries) must not block core CLI/TUI operation.
5. Browser UI binds to localhost until authentication and deployment hardening are implemented.
6. Every release updates `CHANGELOG.md`, `README.md`, this roadmap where priorities changed, and the handoff file.

## Optional deployment track: Docker Compose (PR #5 merged)

- [x] Add a single-container local web runtime and opt-in Telegram bot service, sharing persistent host SQLite/offline/cache state.
- [x] Provide a writable, persistent digest configuration separate from the packaged default.
- [x] Bind the web interface to host localhost only; no public deployment without authentication and origin protection.
- [ ] Verify image build, Compose validation and a real container smoke test on Docker Desktop / GitHub Actions before declaring Docker support stable.
- [ ] Design one nonduplicating container-native scheduler if background jobs must run independently of Windows Task Scheduler.
- [ ] Assess security hardening, smaller optional-dependency image and safe data backup for eventual VPS deployment.


## Security track: isolated development environment (PR #6 merged)

- [x] Add a no-network, non-root, read-only, resource-limited Docker test runner with tmpfs test state and no host mounts.
- [x] Document dedicated Linux VM usage and Codex Cloud/CLI separation.
- [x] Fix owner-only cloud checkout permissions, missing offline test inputs and unnecessary model loading; add PR validation for the restricted Docker runner. See `docs/archive/gate1/DOCKER-AUDIT.md` for local results and build-network limitations.
- [ ] Verify the restricted test runner with Docker Compose build/run on Linux and Docker Desktop; track dependency-related test skips.
- [ ] Pin/audit dependencies and consider reproducible offline build inputs before treating untrusted Dockerfile changes as safe.
- [ ] Add separate Codex devcontainer only after review of sandbox boundaries, secrets, networking and Git credentials.
