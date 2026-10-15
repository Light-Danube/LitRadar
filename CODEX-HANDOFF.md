# Codex development handoff — LitBeacon Research Workspace

## Current — Gate 1 closure and small package setup

- Branch `codex/gate1-package-setup`, main baseline `1d1a2ca6`; #22/#23/#24 are merged and no prior open PR backlog remains. Current code includes venue preservation checks, fixed wheel/data paths and bounded backup/restore. Older “pending” statements below describe their historical increments.
- `scripts/build_user_bundle.py` validates an already-built wheel and emits only wheel + standalone SETUP.txt; metadata/root/bundled versions must agree and release tag must match when supplied. CI installs the extracted wheel on Ubuntu/Windows and uploads a review artifact. Future release attachment replaces the full explicit source ZIP; GitHub automatic source archives remain. No version bump/tag/publication/merge here.
- User confirmed Windows daily use and Narrator work okay on 2026-10-15; record as accepted user-reported evidence, without unprovided versions/task observations or certification. Narrator is optional; broader detailed audit remains optional. Live venue access is still blocked by cloud proxy 403, not a known universal provider defect.
- Gate 1 is complete for this feature-stability candidate once its actual required CI is green; final release approval/versioning, scheduler-specific verification and remaining focused safety checks stay separate. See [current checklist](docs/LOCAL-1.0-RELEASE-CHECKLIST.md) and [package setup](docs/PACKAGE-SETUP.md).
- Executed local full suite: **518 Python / 38 JS passed, 0 failed, 0 skipped**, one Starlette warning. Clean Linux venv installed the extracted setup ZIP's actual wheel with declared web dependencies (plus smoke-only httpx) and passed CLI/assets/web edit/restart/custom DB/default preservation smoke. Syntax/link/whitespace checks passed. Final-head CI must be observed; do not infer Windows setup-ZIP success from these Linux results.
- Actual [Ubuntu/Windows extracted setup ZIP checks](https://github.com/Light-Danube/LitRadar/actions/runs/38657414211) succeeded at code head `3cb012b1`, and both review artifacts uploaded. [Draft PR #25](https://github.com/Light-Danube/LitRadar/pull/25) contains this focused change; use its final head checks to close Gate 1. The later evidence-recording commit changes documentation only.

## Current — bounded Gate 2 recovery (unreleased)

- Final local recovery-branch full suite: **479 Python / 38 JS passed, 0 failed, 0 skipped** (one Starlette warning). Separate disposable integration of packaging/recovery/venue source passed **501 Python tests**; the combined wheel was built/installed outside the checkout and executed CLI backup/new-destination restore/no-overwrite, exact all-table preservation, elected files and browser evidence/artifact downloads. Actual recovery-head CI/Windows remain separate.

- Branch `codex/local-backup-restore`, based on main `448a6ea0` after the Gate 1 audit. User accepted the smallest recovery PR and separate blocker fixes. No major feature, merge, version bump, personal database or service/model access.
- `storage/recovery.py` owns directory bundles; CLI `library-backup` and `library-restore` are distinct from paper-status `restore`. Backup source is direct SQLite `mode=ro`, avoiding PaperStore migrations, and SQLite's backup API captures committed WAL state. Elected exact-layout Research/offline roots require `--writers-stopped`; stopped writers are an explicit user precondition, not a filesystem transaction/automatic lock.
- Manifest version 1 records relative paths/sizes/SHA-256 and exclusions. Private exclusive destination, bounds, portable paths, links/case-collisions, missing/extra files, corruption, SQLite integrity/foreign keys and known FTS-only triggers/virtual-table restrictions. Restore copies then verifies before publishing `litradar.sqlite3`; no overwrite/merge or automatic schema migration. Ordinary failures clean up; process/power interruption may leave an incomplete reserved directory.
- `tests/test_library_recovery.py`: **49 passed / 0 failed / 0 skipped**, Linux Python 3.12.14. Exact all-table round-trip includes user fields/IDs, relations/feedback, annotations/evidence histories and tombstones; elected artifacts, active WAL, bad SQL schema, bounds, injected failures and restored additive legacy metadata schema upgraded twice. Existing v0.1 migration tests are separate. Only synthetic fixtures used.
- Profiles/digest config and scheduler registrations require manual safe preservation/review; credentials are separate, and commands never load them. Checksums do not authenticate an untrusted bundle. README/ROADMAP/USER-GUIDE/checklist record implemented checks and pending candidate CI/clean Windows built-artifact recovery. Packaging blocker fix belongs to its independent focused PR.

## Current — local-only 1.0 freeze, Gate 1 audit

- Branch `codex/local-v1-gate1-audit`, baseline main `b8b42ff4`. Read [release checklist](docs/LOCAL-1.0-RELEASE-CHECKLIST.md) and current ROADMAP before following historical suggestions below. No major features or version bump; 0.8.0 remains current. Real-model quality evaluation and Docker production optimization are not frozen 1.0 blockers.
- PRs #18/#19/#20 are merged; no open PR backlog existed before this audit PR. Historical entries calling #19 open/draft or Windows unverified describe older commits.
- Executed on tracked-source export with synthetic fixtures: Linux Python 3.12.14 **430 passed / 0 failed / 0 skipped**, one Starlette warning; Node 24.19.0 **38 passed / 0 failed / 0 skipped**. Baseline main CI is green, including Windows targeted 129/0/1, Node 38/0/0 and four sandboxed Chrome scenarios. Final Draft PR head checks must be observed separately.
- Built and installed the 0.8.0 wheel into scratch space. CLI import outside source fails with `ModuleNotFoundError: config`; module list omits `config.py`, and wheel inventory lacks `VERSION`/default JSON assets. Fix packaging in a focused defect PR; clean Windows built-artifact and TUI/Narrator checks remain open.
- Smallest next Gate 2 PR: SQLite backup API, bounded checksummed bundle with explicitly elected research/offline files, restore only into a new destination, synthetic corruption/path/WAL/preservation/legacy-upgrade tests and USER-GUIDE instructions. Avoid source migrations while backing up; stop artifact writers. No implementation in this audit.
- Gate 1 remains open for candidate CI and workflow blocker resolution. Preserve personal data and existing APIs; do not merge or publish a release without explicit approval.

## Unreleased — Ukrainian TUI, job crash fix and accessibility evidence

- Branch `codex/tui-uk-accessibility`, based on fetched main `ad4e2a4d`. Read [TUI audit](docs/TUI-ACCESSIBILITY-AUDIT.md) and [menu draft](docs/TUI-MENU-DRAFT.md). Scope is current TUI functionality only; README is intentionally unchanged per user instruction.
- `ui_locales.py` owns EN/UK app strings; `ui.py` selects language at runtime or from `LITBEACON_TUI_LANGUAGE` / legacy alias. Paper data, technical identifiers and provider/CLI diagnostic output stay literal. Framework-owned palette/theme dialogs may retain English. Switching retains filters, query input and selected paper.
- Jobs crashed because Screen lacks `call_from_thread`; scheduler results now dispatch through App with busy/cancellation/mount guards. New tags refresh filter options on modal close. App background callbacks address the main screen while a modal is open.
- Offline-storage exceptions now produce a persistent localized error instead of an unhandled worker failure. Tests intercept all offline/browser operations; no real downloads or external destinations were used.
- Help/details/jobs scroll by keyboard, Close is reachable, focus has a border cue, job buttons stack, online input flexes, and toolbar uses two rows below 110 columns. The complete grouped-menu/pane-switch proposal is still a draft.
- Textual minimum raised to 1.0 in requirements and UI extra; 0.50.1's binding API is incompatible with this implementation. Tested 1.0.0. Module registration includes `ui_locales`; no application release-version bump.
- Final local checks: **430 Python / 0 failed / 0 skipped**, **6 Node test files / 0 failed / 0 skipped**, including **29 TUI tests**. Native ANSI PTY 80×24 and disposable audit-fixture smoke passed separately. One existing Starlette TestClient deprecation warning. Restricted sandbox inter-thread dispatch hung; the same tests passed in the approved executor outside that restriction. Do not classify that as a production defect.
- The user selected Windows Terminal + Narrator. `python scripts/tui_accessibility_fixture.py --language uk` creates a temporary synthetic library with all provider/scheduler/download/browser actions mocked and no personal config/profile loading. `--smoke` checks the fixture headlessly. Actual Narrator speech, Braille, contrast and participant results remain unverified; preserve the unchecked combined accessibility gate and record real outcomes before closing it.
- README changes from PRs #17/#18 were already in latest main, not authored by this patch. Remote CI remains to be observed after push; create a draft PR and never merge automatically.
- Draft [PR #19](https://github.com/Light-Danube/LitRadar/pull/19) confirmed open/draft targeting main; its description records scope, checks and remaining gates. GitHub reported `action_required` for tests, isolated Docker and Windows at head `85d841dc`; tests had no jobs. No remote pass is claimed; inspect checks for subsequent heads separately.

## Unreleased — browser research workspace

- Add a sixth Research section for explicit venue-scoped search and editing the existing evidence worksheets, with EN/UK, preserved drafts and library filters for to-read/new/all. Keep the prior five sections and Alt+1–5; Alt+6 opens Research.
- Add editable topic/venue shortcut cards with local icons, conservative unresolved defaults and revision-guarded changes. Card selection fills the form without a provider request; concrete identity resolution remains explicit.
- Save search pages, worksheet snapshots and Markdown/CSV exports to unique local `data/research/<identifier>/` bundles; generated IDs or validated user names never overwrite existing results. Existing SQLite library and personal notes remain authoritative/intact.
- User reports live CLI API retrieval succeeds locally (2026-10-14); this supersedes an assumption of universal inaccessibility, while historical cloud 403 probes remain separate evidence. No automatic inference or indexing/novelty certification.
- Local checks: **405 Python passed / 0 failed / 0 skipped; 6 Node test files passed / 0 failed / 0 skipped**. Browser rendering blocked before launch by SUID sandbox configuration; Windows/remote CI results not claimed.
- [Browser workflow, storage and verification](docs/research/web-workspace.md) · [quick-topic design](docs/research/quick-venues.md). Release version remains 0.8.0.

## Unreleased — compact documentation and CLI guidance

- Keep README as a compact overview/quick start, with detailed instructions in `docs/USER-GUIDE.md`; AGENTS now records this maintenance rule.
- Add discoverable `venue`/`evidence` help examples and a [Russian practical workflow](docs/research/cli-workflow-ru.md) explaining evidence quality, research use and remaining limits. No retrieval/storage behavior or release version changes. Validation: 298 Python passed / 0 failed / 0 skipped; 5 Node test files passed / 0 failed / 0 skipped; CLI help examples and Markdown links checked.

## Unreleased — venue discovery and evidence worksheet

A CLI-first vertical slice adds opt-in OpenAlex venue lookup and structured source/year search, separate from existing broad discovery. Concrete source IDs distinguish same-name venues. One bounded page is cached with all filters; source metadata, query URL and UTC retrieval time are retained separately from canonical papers. Provider metadata does not certify peer review or Scopus/WoS membership. Existing paper IDs, notes, tags, status, relations and scores survive enrichment; conflicting DOI/provider aliases fail atomically.

Human-editable evidence worksheets retain per-field provenance and revision history, independently of personal notes. Markdown/CSV exports include unknown evidence, venue observations and unverified gap candidates; no LLM calls occur. [Usage, bounds and recovery](docs/research/venue-discovery.md), [implementation contracts](docs/research/implementation-plan.md), and [literature review](docs/research/erc-context-novelty-matrix-2026.md).

Local validation: **298 Python tests passed / 0 failed / 0 skipped; 5 Node test files passed / 0 failed / 0 skipped**. [Executed checks and pending evidence](docs/research/delivery-validation.md).

Browser venue-discovery controls remain planned; retrieved paper IDs are available in the existing Literature inbox. Release version stays 0.8.0. Live OpenAlex and Crossref requests failed at the proxy with `Tunnel connection failed: 403 Forbidden`; fixture tests do not verify live metadata or coverage. Windows, rendered-browser and neural-model evaluations are not claimed.

This file records development progress and a safe starting point for continuing with Codex. The repository is still named `LitRadar` on GitHub, while the public-facing application name is **LitBeacon**.

## Semantic exploration and graph/workflow refinement (unreleased)

- Branch `codex/v08-semantic-graph-workflows`, base main `54f48330`. Read [patch progress/release gates](docs/V08-PATCH-PROGRESS.md), [semantic evaluation](docs/SEMANTIC-WORKSPACE.md) and [Windows smoke](docs/WINDOWS-WORKSPACE-SMOKE.md).
- Semantic exploration is OFF by default and local-only; UI opt-in graph edges are ephemeral related links participating in bounded traversal, never citations. Complete-link clusters are distinct from heuristic grouping. No model download or silent semantic fallback.
- Graphs settle label/node collisions on drag/keyboard changes; native stationary pointer capture is assigned to the node. Export is a details menu; retain keyboard controls and model-provenance labels.
- New mixed-provider/API/EN/UK workflow tests and Windows CI/native Chrome script use synthetic data; screenshots are uploaded only from the unique run directory. No Windows result is claimed here.
- Local checks: Python 186/0/0; Node 28/0/0; restricted Docker 179/0/7 expected optional skips. Corpus lexical controls executed, but neural-model evaluation is blocked by missing local weights/proxy 403. The version remains 0.8.0 until the authorized 0.8.5 gates are confirmed.
- AGENTS.md now contains project map, recovery/security boundaries, optional flags and release verification rules. GitHub API remains Forbidden; after push use the auto-created draft and inspect actual Actions results through the user's GitHub interface.

## Annotation adapters, recovery and graph layout (unreleased)

- Branch `codex/annotation-adapters-graph`, base `ef5ecd06`. Read [the workflow/recovery specification](docs/V08-ANNOTATION-WORKFLOWS.md).
- Add bounded uploaded-file adapters and optional `requirements-annotations.txt` / `[annotations]` extra. Web CI installs the extra parsers; the lightweight isolated image intentionally does not. PDF/BibTeX are parsed in timeout/resource-bounded subprocesses, without opening referenced paths.
- Per-paper fresh inference is off by default, uses provider/model selection and explicit consent, sends only title/abstract and stores generated/unreviewed provenance. Tests mock all three providers; no live service/credential validation.
- Add nullable tombstones to annotations/revisions through additive migrations. Soft delete/undo and paginated version history use expected revision guards. Research-note restoration writes legacy `papers.notes` plus a new `history_restore` row with latest-note guard.
- Graph gestures are in `graph-interactions.js`; node coordinates are browser-local and SVG exports use them. Scientific graph payloads remain unchanged.
- User accepted the baseline visual/functionality on 2026-10-14 and explicitly skipped the extra cloud browser gate. Do not translate this into a new automated browser pass.
- Validation: Python 164 passed / 0 failed / 0 skipped; Node 19 / 0 / 0; restricted Docker with file parsers 159 / 0 / 5 expected skips (Textual 4, Node 1); lightweight profile 157 / 0 / 7 (also PDF/BibTeX). Remote CI remains unreadable through the API; Actions auto-creates draft PRs after push.

## Beacon Blue refinement (unreleased)

- Branch `codex/web-brand-beacon`, based on main `a9152bb1`. Generated local PNG mark/favicon and blue/cyan/gold palette reflect the supplied Telegram reference. See [brand rationale and review gates](docs/ux-research/brand-beacon.md).
- No API/database changes or removed workflows. New package-data glob includes the image. Wordmark contrast is included in Node checks.
- The draft-workflow fake `gh` executable failed on `/tmp:noexec`; it is now a Bash function. Isolation remains intact. Host Python: 147 passed / 0 failed / 0 skipped; Node: 11 / 0 / 0; restricted Python 3.11 Docker: 142 / 0 / 5 expected skips (Textual 4, Node 1).
- Secure Chromium remains blocked; no rendered WebUI screenshots. Remote CI/PR state is not readable through the API. Automatic draft creation has worked according to the user; push a dedicated branch and verify the Actions-created draft through GitHub.

## Quiet Research Phase 1 (unreleased)

- Branch `codex/web-redesign-shell`, based on merged research PR #8 / main `3df12b79`. Shared tokens, light/dark/system themes, responsive shell and localized appearance control are implemented. Theme updates do not rebuild content.
- Existing APIs, schema, workflows, five destinations and 48 feature contracts are retained. `theme.js` loads before CSS; graph exports retain standalone fallback colors.
- Reproduce: Python `python -m pytest -q -ra`; JS `npm ci --prefix tests/web --ignore-scripts` then `npm test --prefix tests/web`. Local results: 144 Python and 11 JS passed, 0 failed, 0 skipped. jsdom is test-only.
- Secure Chromium failed before rendering due to sandbox helper configuration. No new screenshots, browser reflow or full accessibility claim. GitHub PR-list API is Forbidden; do not broaden permissions or create tokens.
- Read [Phase 1 verification and remaining review](docs/ux-research/phase-1.md) and [current public competitor evidence](docs/ux-research/live-review-2026-10-13.md). The user accepted the baseline visual/functionality on 2026-10-14 and skipped the extra cloud-browser gate; this supersedes the original visual gate. Phase 2 remains proposals.

## Starting point

- Repository: `Light-Danube/LitRadar`, default branch `main`.
- Current release at the time of this handoff: **v0.8.0** (verify `VERSION` and `CHANGELOG.md` before changing code).
- Read `README.md`, `ROADMAP.md`, `CHANGELOG.md`, `BRANDING.md`, and `UI-REVIEW-v0.8.md` before planning the next version.
- The local-first Python CLI, Textual TUI, Telegram bot, digest/scheduler, and FastAPI browser workspace share the existing SQLite database. Preserve compatibility with legacy `LITRADAR_*` configuration, `data/litradar.sqlite3`, and Windows launchers.

## Completed increment: citation-map usability (unreleased)

- Feature branch: `codex/citation-map-provenance-filters`, based on the merged v0.8.0 handoff.
- Citation map now has pan/zoom/reset, relation/provider/depth controls, explicit selection and recentering, real citation arrows, and merged edge provenance with observation timestamps.
- `/api/graph` adds `relation=all|cites|related` and optional `provider`. Filters apply before each traversal hop. Edge payloads add `providers` and `provenance` while keeping `provider` for compatibility. Provider filtering refers to relation provenance, not the paper's primary source.
- SQLite schema and legacy workflows are unchanged. Do not interpret edge provenance as note provenance.
- Validation: 117 tests passed without skips on Windows/Python 3.10.11, plus compileall (excluding `.venv`), JS syntax and diff whitespace checks. Supported Python 3.11/3.12 runs require CI. Browser fixture smoke covered filters, selection/provenance, recenter/open-paper, zoom and pan/reset; screenshot is in `docs/screenshots/citation-map-provenance.png`.
- `BRANDING.md` and `UI-REVIEW-v0.8.md` referenced below are absent from the current checkout/remote tree; consult README and ROADMAP for current scope.

## Current increment: annotation provenance (unreleased)

- Branch `codex/annotation-provenance` starts from main after PR #2 merged.
- Additive `paper_annotations` table stores research-note revisions and separate supplemental annotations. The existing `papers.notes` field remains authoritative for old workflows; `set_notes()` updates it and records a revision in one transaction. Unchanged saves do not add a revision.
- Nonempty existing notes backfill once with `kind=legacy`; authorship/original time is unknown. `recorded_at` is UTC ingestion/migration time, not a claimed original authoring timestamp.
- GET/POST `/api/papers/{id}/annotations` lists/adds supplemental entries of user/imported/extracted/generated origin, optional source references and server timestamps. GET uses `limit` (1–200) and `before_id` for stable descending pagination and returns the latest primary note's provenance.
- Web details show the latest research-note provenance, separate annotation cards and an append form. Sources display as plain text and generated suggestions are advisory. Labels describe declared origins; the app does not automatically import/extract/generate material in this increment.
- Ukrainian localization for Web UI and/or TUI is added to the v0.8.x roadmap. No translation has been implemented yet.
- Validation: 129 local tests passed without skips on Windows/Python 3.10.11; compileall excluding `.venv`, JS syntax and whitespace checks passed. Supported 3.11/3.12 validation runs in CI. Browser fixture smoke verified annotation submission/provenance, Unicode/literal markup, persistence and note/draft separation; screenshot: `docs/screenshots/annotation-provenance.png`.

## Current increment: workspace workflows and Ukrainian Web UI (unreleased)

- Branch `codex/workspace-v08-completion` starts from main after PR #3 merged. The four requested roadmap items are checked with the exact supported scope; follow-up items preserve remaining TUI/adapters/audit work.
- Graph year bounds/unknown-year policy filter nodes before traversal; a seed remains visible as context. `web/static/graph-tools.js` implements deterministic BFS layers and standalone SVG/GraphML export. JSON exports the displayed API snapshot and filter metadata.
- `web/annotation_actions.py` imports bounded JSON and extracts stored metadata with content hashes for idempotency. Opt-in generation reuses stored LLM assessment JSON or local heuristic reading prompts; it never calls a model/provider endpoint. Automatic provenance records `origin_method`; manual labels remain declarations.
- Additive annotation columns: `origin_method`, `review_status`, `revision`, `updated_at`, `evidence_key`; `annotation_revisions` retains original/edited versions. PATCH edits require `expected_revision` and preserve original kind/source. Review values are `unreviewed|accepted|dismissed`. Existing note workflows remain unchanged.
- New endpoints: POST `/api/papers/{id}/annotations/import`, POST `…/extract`, PATCH `…/annotations/{annotation_id}`, GET `…/notes/history` with cursor pagination.
- Web interface strings are in `web/static/locales.js`; language selection persists in the browser. English/Ukrainian affects display only, never statuses/config identifiers or source paper content. TUI remains English.
- Validation: 138 local Python tests and 4 Node tests passed; browser fixture covered locales/drafts, import/extraction/opt-in, edit/review/history, graph filters and all downloads. Export files parsed as matching 9-node/9-edge snapshots. Supported Python 3.11/3.12 verification runs in CI.

## Suggested next Codex task

The documentation-only branch `codex/ui-ux-research`, based on main `36d93687`, contains [a web-readability research and design draft](docs/ux-research/README.md). It includes a synthetic standalone HTML concept, 48 feature-preservation contracts and an incremental PR plan. Application files are unchanged. Official competitor pages were blocked by network policy, and Chromium sandbox could not initialize; complete the source ledger and browser/usability validation before treating the design as final. Do not replace existing functionality with the prototype's intentionally partial demo behavior.

Docker audit takes priority over new features. PRs #5 and #6 are merged in main at `7b4034d0`, including `be9b230`. The branch `codex/docker-isolation-audit` fixes offline fixture/workflow packaging, owner-only cloud file access and test-cache placement; it adds PR validation for the isolated runner. Local full-suite results are 144 Python passes and 4 Node passes, with no skips. A restricted Python 3.11 container built from local wheels passed 139 tests with 5 expected optional skips. See `docs/DOCKER-AUDIT.md`; remote CI logs and a stock production-image build remain gates before declaring Docker stable.

Continue optional graph/semantic evaluation or translate Textual TUI. Extend import adapters only with bounded fixtures and preserve source evidence. Define recovery before annotation deletion/history restoration; fresh LLM inference needs explicit opt-in and tests. Perform accessibility/assistive-technology QA without assuming the current contrast/focus improvements imply full compliance.

## Development workflow

1. Create a feature branch from the current `main`; do not commit directly to `main`.
2. Inspect the actual implementation and tests before modifying interfaces or storage.
3. Keep migrations additive and existing data intact. Do not overwrite or commit `.env`, SQLite databases, API keys, Telegram tokens, local caches, downloaded PDFs, or `.venv`.
4. Install dependencies as needed: `requirements.txt`, `requirements-dev.txt`, `requirements-ui.txt`, `requirements-llm.txt`, and `requirements-web.txt`. Heavy/optional packages should not block core workflows.
5. Run `python -m pytest -q` and `python -m compileall -q .`; run `node --check web/static/app.js` if Node is available. For UI changes, smoke-test `python cli.py web` locally. Report skips and unavailable tools explicitly.
6. Update `README.md`, `ROADMAP.md`, `CHANGELOG.md`, and the handoff when scope changes.
7. Open a **draft PR** with a concise summary, test results, migration notes, and screenshots for visual changes. Leave merging to the repository owner.

## Guardrails

- Preserve the local-only binding for the unauthenticated web server; do not expose it publicly.
- Citation/lexical heuristics are not evidence of scientific novelty.
- Use existing graph/storage models where possible; avoid introducing a second database or mandatory frontend build system without a demonstrated need.
- Distinguish tests executed in the environment from CI results not yet observed.

## Historical connectivity smoke test

This document is intentionally the only file added in the initial Codex connectivity PR. Its purpose is to verify branch creation, commit, and draft PR review before handing over larger engineering changes.
