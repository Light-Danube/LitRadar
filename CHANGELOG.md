# Changelog

## Unreleased — Gate 3 Telegram listener diagnostics

- Stop fatal Telegram polling conflicts/configuration failures with a nonzero CLI result, explain common HTTP/network failures safely, and preserve transient retries, Ctrl+C, offsets and nonfatal command-menu setup. A 409 can indicate another poller or a webhook; neither is changed automatically.
- Add timestamped listener diagnostics with optional `telegram-run --debug --log-file PATH` and bounded UTF-8 file rotation. Omit credentials, URLs, IDs, payloads, research/message content and raw exceptions from listener diagnostics. Independent scheduled-digest/chat-discovery transports remain separate.
- Add fake-transport/logging/CLI regression coverage and a targeted Windows CI step. Executed local checks: **589 Python / 38 JS passed**, zero failures/skips, one existing Starlette warning; final built-wheel smoke passed on Linux. Candidate Windows/CI remains pending in [increment validation](docs/GATE3-TELEGRAM-DIAGNOSTICS.md); no personal database, live token, merge, version bump or release.

## Unreleased — Gate 1 archive and packaged recovery verification

- Archive completed Gate 1 plans, audits, validation records, historical screenshots and handoff; retain current setup, user and recovery guides. Repair affected links and shorten the active release checklist.
- Extend the existing installed setup-wheel smoke on Ubuntu/Windows with disposable CLI backup/new-destination restore, durable row/history/tombstone preservation, elected artifacts/checksums, integrity and no-overwrite checks. Runtime behavior and version remain unchanged. Local candidate checks: 518 Python / 38 JS passed, zero failures/skips; fresh Linux setup-wheel smoke passed. Actual [Ubuntu/Windows packaged recovery CI](https://github.com/Light-Danube/LitRadar/actions/runs/38744388702) succeeded at implementation head `a9c64fb2`; the active checklist records limits and final-head check status.

## Unreleased — small package setup and Gate 1 closure

- Build a version-checked setup ZIP containing only the runtime wheel and short `SETUP.txt`, with explicit venv commands, data locations and upgrade/backup guidance. Future published releases attach this ZIP and wheel after smoke validation; ordinary users need no source checkout/legacy docs. No version/tag/release is created here.
- Verify installation from the extracted ZIP on Ubuntu/Windows CI; refuse unrelated/private wheel content, version/tag disagreement and artifact overwrites. Existing source launchers and optional components remain available.
- Consolidate merged Gate 1 fixes/evidence and the user's 2026-10-15 Windows daily-use/Narrator acceptance. Narrator is optional; user-reported acceptance is not a formal audit. Gate 1 closes with green candidate checks; later release gates and environment-blocked live venue verification stay explicit.
- Executed local full suites: **518 Python / 38 JS passed, 0 failed, 0 skipped**, one existing Starlette warning; clean extracted-package dependency install and CLI/static-assets/web-edit/restart smoke passed. Actual [Ubuntu/Windows setup ZIP checks](https://github.com/Light-Danube/LitRadar/actions/runs/38657414211) succeeded at code head `3cb012b1`, with downloadable review artifacts; final PR-head checks remain the closure evidence.

## Unreleased — bounded local library recovery (Gate 2)

- Add `library-backup`: SQLite backup API on a read-only source, no source migration, private new-directory bundle with versioned manifest/SHA-256 and explicitly elected Research/offline artifacts. Including files requires acknowledgment that artifact writers are stopped; credentials, logs/caches, models, profile/digest config and scheduler registrations are excluded.
- Add `library-restore`: bounded validation and restore into a new directory only, no overwrite/merge or automatic database switching. Validate checksums, portable paths, links, executable schema restrictions and SQLite integrity/foreign keys before success; clean up ordinary failures. Preserve existing paper-status `restore` command.
- Synthetic targeted tests: **49 passed / 0 failed / 0 skipped** on Linux Python 3.12.14; active WAL, exact table/history/tombstone preservation, elected files, corruption/path/schema rejection, cleanup and repeated restored legacy upgrade. Full candidate CI/Windows artifact checks remain separate; no personal database, external services, major new features or release-version bump.
- Full recovery-branch checks: **479 Python / 38 JS passed, 0 failed, 0 skipped**, one existing Starlette warning. A disposable integration checkout with the separate packaging/venue changes passed **501 Python tests** and an installed-wheel recovery/web-artifact smoke; this is local integration evidence, not the published recovery PR's Windows result.
- Document [recovery commands, exclusions, manual profile/scheduler preservation and limits](docs/USER-GUIDE.md#consistent-local-backup-and-restore-unreleased).

## Unreleased — local-only 1.0 Gate 1 audit

- Freeze major feature development and add an [evidence-based release checklist](docs/LOCAL-1.0-RELEASE-CHECKLIST.md) covering existing workflows, merged PRs, CI profile skips and remaining gates.
- Execute combined synthetic Linux checks: **430 Python / 38 JS passed, 0 failed, 0 skipped** (one Starlette deprecation warning). Observe actual green baseline CI, including Windows API/DOM and four native Chrome scenarios; these do not establish clean Windows artifact installation or Narrator validation.
- Reproduce a built-wheel CLI import failure (`config.py` omitted); inventory missing `VERSION` and default JSON assets. Record recovery/upgrade gaps and the smallest next local backup/new-destination restore PR. Documentation only; no feature changes, personal data access, merge or release-version bump. Final candidate CI remains a separate check.

## Unreleased — Ukrainian Textual TUI and job crash fixes

- Add EN/UK TUI language selection, translated app bindings/status/sort/detail/help/activity/job controls and notifications. Preserve raw paper data, provider/CLI diagnostics and identifiers; startup language can use `LITBEACON_TUI_LANGUAGE` or its legacy alias.
- Fix scheduler thread results dispatched through App, prevent repeated commands while busy, recover controls after errors/timeouts and ignore late results after dialog closure. Refresh new tags in the filter immediately after saving.
- Keep the TUI alive on offline-storage errors and retain the localized failure in the activity panel; test PDF/metadata outcomes and intercepted PDF/DOI opening.
- Add keyboard-scrollable help/details/jobs, explicit help Close, visible focus, vertically stacked job controls, a flexible online input and two-row toolbar below 110 columns. Keep the full grouped-menu redesign as a [draft](docs/archive/gate1/TUI-MENU-DRAFT.md).
- Require Textual >=1.0,<2 in both UI installation paths and include the localization module in package metadata. Existing release version remains 0.8.0.
- Add synthetic workflow/localization tests and a disposable [Windows Terminal + Narrator audit fixture](docs/TUI-ACCESSIBILITY-AUDIT.md). **430 Python passed / 0 failed / 0 skipped; 6 Node files passed / 0 failed / 0 skipped**; 29 TUI tests, ANSI PTY and fixture smoke passed. One existing Starlette deprecation warning. Full assistive-technology audit and remote CI remain unverified; no README changes.

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

Human-editable evidence worksheets retain per-field provenance and revision history, independently of personal notes. Markdown/CSV exports include unknown evidence, venue observations and unverified gap candidates; no LLM calls occur. [Usage, bounds and recovery](docs/research/venue-discovery.md), [implementation contracts](docs/archive/gate1/research/implementation-plan.md), and [literature review](docs/archive/gate1/research/erc-context-novelty-matrix-2026.md).

Local validation: **298 Python tests passed / 0 failed / 0 skipped; 5 Node test files passed / 0 failed / 0 skipped**. [Executed checks and pending evidence](docs/archive/gate1/research/delivery-validation.md).

Browser venue-discovery controls remain planned; retrieved paper IDs are available in the existing Literature inbox. Release version stays 0.8.0. Live OpenAlex and Crossref requests failed at the proxy with `Tunnel connection failed: 403 Forbidden`; fixture tests do not verify live metadata or coverage. Windows, rendered-browser and neural-model evaluations are not claimed.

## Unreleased — semantic exploration, graph collision handling and workflow verification

- Add OFF-default local-only embedding related edges/complete-link clusters, bounded cohorts, explicit UI selection and computed provenance. Existing citation records and heuristic defaults are retained.
- Add deterministic node/label collision settling, ordinary click capture fix, accessible export dropdown and retained keyboard zoom/selection controls.
- Extend mixed OpenAlex/Semantic Scholar/API/EN/UK DOM tests and a Windows native-Chrome workflow with synthetic screenshot artifacts. Expand AGENTS.md for continuation.
- Local validation: Python 186 passed / 0 failed / 0 skipped; Node 28 / 0 / 0; restricted Docker 179 / 0 / 7 expected optional skips. Native Windows and real neural-model evaluation remain pending; no conditional 0.8.5 bump yet. See [patch status](docs/archive/gate1/V08-PATCH-PROGRESS.md).

## Unreleased — annotation adapters, recovery and graph layout

- Add atomic multi-file JSON/RIS/BibTeX/PDF annotation import with bounded uploaded bytes, optional local parsers and repeat-safe provenance. Existing JSON API remains compatible.
- Add per-paper opt-in fresh OpenAI/Anthropic/Ollama inference with provider/model selection, bounded metadata input, transport limits and generated/unreviewed provenance. No personal-note overwrite or automatic inference.
- Define reversible deletion, paginated supplemental version history and append-only annotation/research-note restoration with optimistic guards; additive migrations retain old data.
- Add cursor-anchored wheel zoom, node dragging, keyboard movement, local layout persistence/reset and geometry-aware SVG export, with EN/UK labels.
- Record user acceptance of the existing visual/functionality and skip the extra cloud-browser gate as requested. Local checks: Python 164/0/0, Node 19/0/0; restricted Docker with file adapters 159/0/5 expected optional skips (Textual/Node), lightweight profile 157/0/7. Live providers, Windows and new real-browser rendering are unverified. See [workflow documentation](docs/V08-ANNOTATION-WORKFLOWS.md).

## Unreleased — Beacon Blue web identity

- Add a generated, transparent reader-robot/book/beacon mark inspired by the supplied Telegram icon; use it in the sidebar and favicon, and include it in Python package data.
- Refine light/dark semantic palettes around navy, ocean blue, cyan and gold while retaining EN/UK, the five sections and existing workflow/API contracts. Palette tests include the wordmark contrast.
- Fix isolated-runner workflow tests that tried to execute a temporary fake `gh` under `/tmp:noexec`; use a Bash function without changing Docker security settings.
- Local checks: Python **147 passed, 0 failed, 0 skipped**; Node **11 passed, 0 failed, 0 skipped**; restricted Docker **142 passed, 0 failed, 5 expected skips** (4 Textual, 1 Node). Generated-icon inspection and wheel asset inclusion verified; application browser rendering remains blocked by Chromium sandbox configuration. See [brand notes](docs/archive/gate1/ux-research/brand-beacon.md).

## Unreleased — automatic draft PR workflow

- Open a draft PR for the pushed `codex/*` branch instead of relying on generated working-tree changes; avoid duplicate open PRs and stop when listing fails.
- Keep repository-scoped Actions permissions; no automatic merge or primary-branch push. Add mocked-runner regression tests and include only their required workflow source in the Docker test context.
- Local Python validation: 147 passed, 0 failed, 0 skipped. Actual GitHub Actions execution remains to be confirmed.

## Unreleased — Quiet Research Web UI, Phase 1

- Introduced shared semantic design tokens, light/dark palettes, responsive navigation and grouped controls, readable typography and visible keyboard focus.
- Added localized System/Light/Dark appearance selection, applied before CSS and persisted locally; appearance changes preserve editor DOM, unsaved inputs and graph viewport.
- Kept the five sections, existing API/database contracts, EN/UK, shortcuts and all documented feature contracts; standalone graph exports retain their self-contained palette.
- Added locked test-only DOM regressions and palette/graph checks to web CI. Local validation: Python **144 passed, 0 failed, 0 skipped**; JavaScript **11 passed, 0 failed, 0 skipped**.
- Read current public competitor sources and documented their evidence limits. Secure Chromium rendering remains blocked by the environment sandbox configuration; visual acceptance/screenshots and GitHub CI status are unverified. See [Phase 1 notes](docs/archive/gate1/ux-research/phase-1.md).

## Documentation draft — web readability research

- Added a Ukrainian UX audit, provisional competitor comparison with an explicit source-access ledger, paired light/dark visual direction, a standalone synthetic-data HTML concept, and an incremental implementation/usability-testing plan.
- Recorded 48 current web feature contracts to preserve during a future redesign. No application functionality, API, schema, or release version changes in this research draft.
- Live competitor pages and sandboxed browser rendering were unavailable in the research environment; those validation gates remain open.

## Unreleased — isolated Docker development audit

### Fixed
- Copy dev-image source with ownership matching UID 10001 so owner-only cloud checkouts remain readable without root tests or world-readable files.
- Include only the two CI workflow manifests needed by offline contract tests while continuing to exclude research data and secrets from the build context.
- Generate disposable CLI smoke-test inputs instead of reading excluded `data/fixture.json`, and explicitly use keyword scoring without model downloads.
- Match lightweight core/web CI dependencies in the dev image and keep pytest cache in writable ephemeral `/tmp`.

### Validation
- Added a read-only-permissions GitHub Actions workflow to build and run isolated Docker tests on PRs.
- Local Python 3.12: **144 passed, 0 failed, 0 skipped**; Node: **4 passed, 0 failed, 0 skipped**.
- Restricted Python 3.11 container with locally downloaded wheels: **139 passed, 0 failed, 5 expected skips** (4 Textual, 1 Node). Its boot helper served a synthetic paper through the web API with no network or host mounts.
- Stock Docker build networking and GitHub API access are unavailable in this cloud session. Production-image build and current/historical CI logs remain unverified; see `docs/archive/gate1/DOCKER-AUDIT.md`.

## Unreleased — v0.8.x workspace workflows and Ukrainian Web UI

### Added
- Deterministic layered graph layout, inclusive year filters with unknown-year handling before traversal, and client-side standalone SVG/GraphML/JSON exports of the displayed snapshot.
- Atomic, bounded, idempotent JSON annotation import and stored-metadata extraction; generated suggestions require opt-in and reuse stored assessments or local heuristic reading prompts, with adapter/source provenance and no network inference.
- Annotation accept/dismiss/reopen/edit actions with optimistic revision checks and retained edit history; paginated research-note history UI including cleared/legacy notes.
- Externalized English/Ukrainian Web UI strings, persisted language selector, localized help/status/actions and preserved unsaved note/form drafts.
- Onboarding instructions, semantic paper buttons and form labels, skip link, keyboard shortcuts, visible focus, improved muted-text contrast, loading/empty/retry states and stale page-response guards.

### Compatibility and limits
- SQLite migrations only add annotation metadata columns, an evidence index and `annotation_revisions`; existing primary notes and CLI/TUI/Telegram identifiers/workflows remain intact. No mandatory dependency or release-version change.
- Supported import is JSON; extraction uses metadata already stored in SQLite. No automatic PDF parsing, new LLM calls, annotation deletion or history restoration. Textual TUI localization and a full assistive-technology audit remain planned.

### Validation
- Windows/Python 3.10.11: **138 Python tests passed**, no skips; **4 Node tests passed**. One existing Starlette/httpx TestClient deprecation warning. Supported Python 3.11/3.12 runs are verified in CI.
- Tests cover migration, import atomicity/idempotency, opt-in/adapters, edits/conflicts/provenance retention, note-history pagination, year filters/traversal and XML/Unicode export validity. Node checks cover dense layout and locale-key/interpolation coverage.
- Browser fixture smoke verified English/Українська and draft preservation, JSON file import, metadata extraction with/without generation, edit/review/history, filtered graph keyboard selection and all three downloads. Downloaded SVG/GraphML/JSON parsed with matching 9 nodes/9 edges and 2020–2023 bounds. An initial stale cached HTML load needed reload; the HTML response now disables caching.

## Unreleased — v0.8.x annotation provenance

### Added
- Additive SQLite `paper_annotations` table for separate user/imported/extracted/generated annotations with source references and UTC recording timestamps. Original notes are backfilled once with explicit unknown legacy provenance.
- Atomic research-note revision recording through the existing `set_notes()` workflow, including clearing a note; unchanged saves do not create duplicate revisions. The legacy `papers.notes` field stays authoritative for CLI/TUI, search, exports and offline bundles.
- Web paper-detail form and bounded, cursor-paginated GET/POST annotation endpoints. Imported/generated material remains separate from personal notes; generated suggestions are visibly advisory. Source references render as plain text.
- Roadmap item for Ukrainian Web UI and/or Textual TUI localization, language selection and Unicode workflow verification.

### Compatibility and limits
- No database reset or new dependency; existing CLI/TUI/Telegram interfaces and local-only binding remain intact. Release metadata remains v0.8.0.
- Origins are user declarations; timestamps show local recording time. Automatic import/extraction/generation, annotation edit/delete, history UI and supplemental search/export remain future work.

### Validation
- Windows/Python 3.10.11 local suite: **129 passed**, no skips; one existing Starlette/httpx TestClient deprecation warning. Supported Python 3.11/3.12 checks run in CI.
- Tests cover idempotent legacy-note migration, note/revision rollback, unchanged and cleared notes, Unicode, provider refresh preservation, validation, cascade behavior and stable API pagination.
- Repository compileall excluding `.venv`, JavaScript syntax and whitespace checks passed. Loopback browser fixture smoke verified origin labels, source references, advisory suggestions, Unicode/literal markup display, persistence after reload, and research-note saving without clearing a supplemental draft. No browser console errors observed; screenshot: `docs/archive/gate1/screenshots/annotation-provenance.png`.


## Unreleased — v0.8.x citation-map usability

### Added
- Native SVG pan by background drag, bounded zoom/reset controls, and node selection via click, Enter, or Space. Selection shows directional neighbor labels and provider observation timestamps, with separate open-paper and explore-neighborhood actions.
- Relation type, edge provider, and depth controls, plus filter reset. Edge filters apply at every traversal depth and in the returned graph.

### Fixed
- Citation arrows now point from citing to cited paper; undirected related links remain dashed.
- Duplicate provider observations are displayed as one relationship with complete provenance. API edges keep the legacy `provider` field and add `providers`/`provenance`.
- Bounded results are deterministic; `truncated` reports actual omissions rather than simply reaching exactly the node limit. Unseeded graph requests honor the requested maximum up to 200 nodes.

### Compatibility and limits
- No SQLite migration, mandatory dependency, or CLI/TUI/Telegram interface change. Released version remains v0.8.0 until a release is prepared.
- User/imported/generated annotation provenance, year filters, exports, and improved layout remain future work. Screenshots use a disposable fixture database.

### Validation
- Windows local run: **117 passed**, no skips; one existing Starlette/httpx TestClient deprecation warning. Local `.venv` uses Python 3.10.11; supported Python 3.11/3.12 validation remains with CI.
- Repository `compileall` (excluding `.venv`), JavaScript syntax check, and `git diff --check` passed.
- In-app browser smoke test on loopback with a disposable SQLite fixture verified arrows, merged provenance, Enter/Space selection, recenter/open-paper navigation, filters/reset/empty results, zoom, and background pan/reset. No browser console errors were observed. Screenshot: `docs/archive/gate1/screenshots/citation-map-provenance.png`.

## 0.8.0 — LitBeacon browser research workspace — 2026-10-12

### Added
- Added the first local browser workspace, served by FastAPI/Uvicorn, with overview, searchable/filterable literature inbox, paper details, and editable status/tags/notes.
- Added a bounded native-SVG graph view for citation and related-work relations already stored in SQLite. Relation direction is preserved; graph depth and node count are limited.
- Added exploratory literature-cluster cards using existing tags, repeated venues, and shared title/abstract terms. These groups are explicitly labeled heuristic and are not presented as semantic findings.
- Added local workspace endpoints for library summaries, paper search/editing, graph traversal, clusters, job status, default job installation, and per-job removal.
- Added `requirements-web.txt`, optional `web` package extra, packaged HTML/CSS/JS assets, and a dedicated CI job for web tests plus JavaScript syntax checking.
- Added browser launcher `run_web.bat`; the shared Windows setup and update scripts now install core, UI, development, LLM, and web requirements.
- Added persistent CLI shell launcher `run_cli.bat` and safer helper behavior for running the optional web server.
- Added `ROADMAP.md`, `BRANDING.md`, and a v0.8 UI/stack review. Updated the GitHub release workflow to produce `LitBeacon-<tag>.zip` archives.
- Recommended LitBeacon Research Workspace as the visible product name after finding exact/near-exact LitRadar uses in the scholarly-literature tooling space.

### Changed
- Updated visible CLI, TUI, web, scheduler-helper and README branding to **LitBeacon Research Workspace (formerly LitRadar)**.
- Retained legacy Python package/module/file names, `LITRADAR_*` variables, database path, and scheduled-task identifiers so upgrades do not orphan local data or existing Windows jobs.
- Added per-job scheduling removal/disable controls in CLI, TUI and Telegram: removing scan need not remove digest, and vice versa. Disabled jobs are skipped even if a stale cron/launchd entry still invokes the scheduled command.
- Updated README and roadmap to distinguish implemented citation graph/heuristic grouping from planned embedding-based semantic edges and evaluated clusters.
- Kept the web workspace loopback-only. No authentication is provided in this release, so it must not be exposed to LAN or public hosts.

### Design decisions
- Choose FastAPI + Uvicorn over a new Node/React deployment for the first browser UI. Existing Python services and SQLite remain the source of truth; HTML/CSS/vanilla JavaScript/native SVG minimize runtime dependencies and work from the packaged wheel.
- Do not label heuristic tag/venue/term clusters as semantic clusters. Embedding-based edges remain an optional future feature gated by evaluation and opt-in dependencies.
- Keep the rebrand compatibility-aware. `LitRadar` remains in package/file/config/task identifiers for now; a public GitHub repository rename or legal trademark clearance is a separate decision.

### Validation
- Local result: **110 passed, 4 skipped**. The four skips are optional Textual UI tests because Textual is absent in the build environment. An attempted install was blocked by this environment’s DNS/PyPI access, so those optional tests could not be enabled here.
- `node --check web/static/app.js` and `python -m compileall -q .` passed.
- Test suite includes disposable SQLite/FastAPI checks for page/API serving, annotation updates/validation, bounded graph traversal and edge direction, plus job removal semantics and Telegram commands.
- Full GitHub Actions was not run remotely. Live Telegram polling, real Windows Task Scheduler changes, and manual Windows UI smoke tests remain to be verified on the user's machine.
- Name review identifies real product-name collisions but is not legal trademark clearance.


## 0.7.1 — interactive Telegram and launchers — 2026-10-10

### Added
- Added a private, long-polling Telegram command listener with Telegram's command menu and inline action buttons.
- Added `/start`, `/help`, `/digest`, `/scan`, `/schedule`, `/settings`, `/topics`, `/topic add|remove`, `/search`, `/recent`, `/queue`, `/limit`, `/overlap`, and `/stats` commands.
- Added configurable daily/weekly digest schedule and time through Telegram; Windows updates the existing Task Scheduler task. Weekly schedule is Sunday.
- Added bounded customization for digest paper count (1–30), queue display count (0–10), overlap section, and up to 10 saved research queries (200 characters each).
- Added persisted Telegram long-poll offset under `data/telegram_bot_state.json`, single-chat allowlisting, error feedback, and protection against duplicate listeners via Telegram's conflict errors.
- Added `run_cli.bat` for a persistent activated CLI shell, `run_telegram_bot.bat` for the interactive command listener, and `setup_litradar.bat` as a shared dependency/database setup helper.
- All Windows/POSIX launchers and the Git updater now install all four sets: core, UI, development, and LLM dependencies.

### Changed
- Added `digest.include_overlap` (default `true`) so overlap warnings can be hidden without disabling scan ingestion.
- Updated package/version metadata and dependency marker to `0.7.1`.
- Refactored Windows launchers to use the shared setup helper; initialization is run before TUI/CLI sessions and after updater dependency refresh.
- The bot only responds to the configured `LITRADAR_TELEGRAM_CHAT_ID`; scheduled digest delivery remains independent of the listener process.

### Design notes
- Windows Task Scheduler remains responsible for daily/weekly background scan and delivery; the bot long-poll process is only needed to receive interactive commands/buttons. This keeps scheduled delivery functioning even if the command-listener window is closed, but interactive commands will not respond while it is stopped.
- Digest schedule customization supports daily and weekly intervals only to keep cadence predictable and avoid adding unnecessary scheduler complexity.
- Inline commands edit `digest_config.json` atomically and keep limits conservative. Complex query editing remains available through the JSON file.

### Validation
- Offline tests cover Telegram polling offsets, configured-chat authorization, command registration, topic CRUD, bounds, schedule configuration, and digest settings.
- Local result: **101 passed, 4 skipped**. The four skipped tests are optional Textual UI tests because Textual is absent in the current build environment.
- No live Telegram send/poll, Windows Task Scheduler modification, or remote GitHub Actions run was performed. These still need real Windows verification.

## 0.7.0 — research digest and scheduled scanning — 2026-10-10

### Added
- Added editable `digest_config.json` with named topic queries, per-source limits, source selection, keyword-only default for background scans, digest/queue limits, and overlap-warning thresholds.
- Added `python cli.py scan` to run configured topics through the shared search/ingest pipeline and record each run in SQLite `research_runs`. Uses the local library/database and dedup layer rather than a separate cloud database.
- Added `python cli.py digest --period daily|weekly` with new-paper summaries, ranking/profile signals, DOI/URL links, possible overlap alerts, and to-read queue summary; writes Markdown when `--output` is supplied.
- Added local heuristic overlap warnings using weighted lexical/TF-IDF cosine similarity against existing catalog records plus already-stored high-overlap LLM assessments. Warnings are explicitly advisory and do not assert lack of novelty.
- Added optional direct Telegram delivery through the official Bot API using Python standard-library HTTPS; messages are split below the API size limit, sent results are recorded in `digest_deliveries`, and `python cli.py telegram-chats` lists recent chat identifiers without printing message contents.
- Added Windows Task Scheduler installation/status/removal commands, a PowerShell task helper and a one-click installer for daily scan + weekly digest. Each one-shot task logs to `logs/`; scheduled digest output is saved to `reports/` when Telegram is not configured.
- Added schema tables `research_runs`, `digest_deliveries`, and `digest_delivery_papers`; migrations are additive and retain the existing paper database, offline files, API caches, and `.env`.
- Citation-discovered new papers now receive a keyword relevance score based on `research_profile.json`; known records retain their previous semantic score when seen via citation traversal or a keyword-only scheduled scan. The TUI citation activity shows this score.

### Design decisions
- Use Windows Task Scheduler (and cron/launchd on Unix-like systems) rather than an in-process APScheduler service. LitRadar is a local CLI/TUI app, so a native OS scheduler runs jobs while the TUI is closed and requires no new mandatory package or permanently running process.
- Default scheduled scans to keyword ranking. This avoids expensive model downloads and minimizes unattended-job failure modes. Semantic scoring can be enabled explicitly in `digest_config.json` when the environment is prepared for it.
- Telegram is optional and sends only after the user configures their own bot token and chat ID in `.env`; secrets are not stored in `digest_config.json`, logs, or the database. No ChatGPT integration plugin is required.
- Digest previews never count as a successful delivery. Only successful Telegram sends advance the per-channel digest cursor, so a failed send can be retried. Local-only scheduled reports do not pretend to have been delivered.

### Validation
- Offline tests cover scan config validation, per-query scheduling, run-history persistence, digest content/reading queue, overlap heuristics, Telegram chunking/delivery requests, loading `.env` for manual Telegram commands, scheduler command discoverability, and preservation of semantic scores.
- Final local result, including tests after applying the patch to clean v0.6.0 and running the full ZIP: **91 passed, 4 skipped**. Four skipped tests are optional Textual UI tests because Textual is unavailable in this environment. No live scholarly API, Telegram send, Windows Task Scheduler registration, or remote GitHub Actions run was performed.
- First Windows installation should be smoke-tested with `python cli.py schedule status --job all`, a manual `python cli.py scan`, and `python cli.py digest --period weekly --output reports/smoke.md` before enabling automatic Telegram sends.

## 0.6.0 — citation intelligence — 2026-10-09

### Added
- OpenAlex citation adapter for a work's `referenced_works`, works that cite it, and `related_works`; related IDs are batch-fetched rather than queried one at a time.
- Semantic Scholar adapter for reference and citing-paper endpoints, with request pacing for its shared unauthenticated quota.
- Bounded breadth-first graph exploration via `python cli.py explore ID` and TUI `C`; the TUI uses a background worker and the persistent activity panel.
- Durable SQLite `paper_identifiers`, `paper_relations`, and `citation_fetches` tables with indexes, provenance, normalized identifiers, cache TTL, and additive migrations/backfill.
- Cross-source identifier reconciliation for DOI, versionless arXiv ID, OpenAlex ID, Semantic Scholar paper ID, PMID, PMCID, and Semantic Scholar corpus ID; added regression coverage for same-title papers with distinct explicit DOIs.
- Bound controls: depth 1–2, 1–100 papers per provider/direction, and 1–200 unique traversal nodes.

### Design decisions
- No extra graph library: SQLite persists edges and supports bounded neighbor traversal; adding NetworkX/igraph would expand dependencies without improving the core retrieval/storage task.
- OpenAlex and Semantic Scholar remain the first providers because both are already integrated. OpenCitations is documented as a future adapter, not another dependency/API path in this release.
- Citation direction is consistently `citing -> cited`; `cited-by` is an incoming query and is stored as neighbor -> seed. Related-work pairs are undirected and stored separately.
- API results are cached for seven days by default. The cached requested limit is tracked, so increasing `--limit` forces a wider lookup. Use `--refresh` to bypass the cache; failed lookups get a shorter retry window.
- Newly discovered records enter the normal library so they can be filtered, tagged, read, or exported through existing workflows.

### Compatibility
- Existing databases are migrated additively and backfilled from stored source references; no database reset is required.
- No new mandatory package or API key was added. The existing OpenAlex and Semantic Scholar keys remain optional configuration, though configuring them is recommended for dependable API access/quota.

### Testing and limits
- Offline API mocks cover OpenAlex references/cited-by/related parsing, Semantic Scholar directional wrappers, edge direction, cache behavior, identifier linking, bounds, and CLI discoverability.
- Graph-degree ranking queries only edges touching the bounded subgraph rather than scanning the full relation table.
- Local run: `78 passed, 4 skipped`; all four skips are optional Textual UI tests because Textual is not installed in the current build environment. No live external API call was used as a test.

## 0.5.4 — TUI progress and Windows updater diagnostics — 2026-10-09

- Replaced transient successful-search toast with a persistent TUI activity panel showing the query, per-provider status, ranking, saving, and a progress bar. The final fetched/new/library counts remain visible in the main screen.
- Added pipeline phase events so slow ranking/saving phases are distinguishable from a stalled network request; CLI also prints these phase events.
- Made `update_litradar.bat` display an exit result and pause before closing, so error messages cannot disappear on double-click.
- Clarified the non-Git/ZIP installation case in the updater: it now reports that no update was pulled and explains how to proceed.
- Made the Rich highlighting test work with both string-based and object-based `Span.style` values across Rich versions; added coverage for persistent progress UI and updater diagnostics.


## 0.5.3 — search and citation primitives — 2026-10-09

### Added
- SQLite FTS5 full-text search across title, abstract, venue, and personal notes, maintained by triggers and rebuilt for existing libraries on initial index creation.
- Graceful `LIKE` fallback for SQLite builds without FTS5.
- Reference-count and influential-citation-count fields where providers expose them; sort choices for both metrics.
- TUI search-term highlighting in the displayed abstract and a dedicated `I` action to open a paper's DOI link.
- Markdown literature-notes export and a structured external-editor note template.
- `pyproject.toml` packaging entries for `pipeline` and `notes`, with optional semantic/UI/LLM dependency groups.

### Changed
- BibTeX citation keys are normalized to lowercase and support `Surname, Given` and `Given Surname` author formats; collisions still receive numeric suffixes during bulk export.
- Bulk offline downloads report progress per paper.
- A successful PDF retrieval removes stale error/status files from a previous failed attempt.
- The Textual CI job installs UI dependencies so UI tests are exercised rather than skipped in GitHub Actions.

### Compatibility
- FTS5 setup is additive; existing databases are not reset.
- Search remains usable if the local SQLite build does not support FTS5.

## 0.5.2 — offline retrieval and note workflow — 2026-10-09

### Added
- Optional Unpaywall DOI resolver via `UNPAYWALL_EMAIL`, only for legal open-access locations returned by Unpaywall.
- PDF signature validation (`%PDF-`), bounded download size, atomic `.part` writes, and protection against saving HTML error pages as PDFs.
- Readable PDF file names based on year, first author, and normalized title, while retaining per-paper offline bundles.
- Structured Markdown note editing through `EDITOR` / `VISUAL` and Windows Notepad fallback.
- `python cli.py export-notes --status read --output literature_review_draft.md`.

### Changed
- Provider direct PDF URLs are tried first; Unpaywall is used as an optional fallback and cached locally.
- Metadata and abstract are still saved even if no legal/open PDF can be retrieved.

## 0.5.1 — workflow and search UX — 2026-10-09

### Added
- Cross-platform quick launch scripts: `run_litradar.bat`, `run_litradar.ps1`, and `run_litradar.sh`.
- Git-checkout update helpers that check tracked changes, pull fast-forward only, update dependencies, migrate the database, and run tests.
- GitHub Release workflow that attaches a clean source ZIP automatically when a release is published.
- Live per-source progress in CLI and TUI, with counts for fetched results, new unique papers, and total library size.
- Online source search from inside the TUI, separate from local saved-library filtering.
- Human-readable rationale for personalized recommendations based on the matching research-profile groups and learned feedback directions.

### Changed
- Updating a Git checkout no longer requires replacing the project folder with a new ZIP.
- Source-query operations share a `search_and_ingest` service so CLI and TUI produce the same summary and data path.


## 0.5.0 — 2026-10-08

### Added
- Runtime `.env` configuration via `python-dotenv`.
- `python cli.py config` for an effective configuration summary with secrets masked.
- Source registry with adapter-based provider definitions and `LITRADAR_SOURCES` enable/disable configuration.
- Concurrent source fetching with configurable worker count.
- Shared HTTP retry/backoff layer for transient provider failures (`429`, `5xx`, connection/timeouts).
- Local source-query cache with configurable TTL to reduce repeated API calls during research.
- Explicit paper feedback events (`positive` / `negative`) stored separately from workflow status.
- Conservative, transparent personalized ranking based on explicit feedback plus weak workflow signals.
- `personalized` sorting in CLI and TUI.
- TUI `Y` / `N` shortcuts for useful/not-relevant feedback.
- New personalization controls: weight, minimum feedback threshold, and candidate scan limit.

### Changed
- Search now uses the source registry instead of hard-coded provider dispatch.
- Provider clients accept configurable timeout/retry settings.
- OpenAlex configuration now exposes `OPENALEX_API_KEY`; the old `LITRADAR_MAILTO` setting remains only for compatibility/documentation because the pre-2026 polite-pool mechanism is no longer the production path.
- TUI displays the personalized score when `Personalized` sorting is selected while retaining the base relevance score in details.
- README restructured around installation, configuration, workflow, personalization, development, and roadmap.

### Design decisions
- Personalization is gated until enough paper-level feedback exists, preventing early overfitting to a handful of actions.
- Manual tags are not automatically interpreted as positive preferences because workflow tags do not necessarily represent topical interest.
- Duplicate dismissals contribute neutral preference evidence.
- Source caching is opt-out via `LITRADAR_SOURCE_CACHE_TTL=0` and cached results are kept outside Git.

### Compatibility
- Existing v0.4.x SQLite databases are migrated additively.
- Existing CLI workflows remain supported.
- No database reset is required.

### Testing focus
- 46 tests covering existing behavior plus personalization, source registry, cache, retry, explicit feedback, environment configuration, and CLI parser paths.
- Textual UI tests remain optional in the local environment and run in the dedicated CI UI job when the dependency is installed.


## 0.4.6 — TUI startup hotfix

### Fixed
- Tag filter now starts with an explicit `All tags` option instead of an empty, non-blank `Select`.
- Prevented TUI startup deadlock/error before the user has an opportunity to choose a tag.
- Added a regression test for the initial tag-filter state.


## 0.4.5 — 2026-10-08

### Added
- TUI tag filter with dynamically loaded manual + source-derived tags.
- TUI `K` shortcut to focus the tag filter.
- Citation count in the TUI paper detail view.
- Matching-paper count in the TUI and `Showing X of Y` output for CLI `list`.
- Automatic source-tag extraction from OpenAlex keywords, Semantic Scholar fields of study, and arXiv categories.
- Conservative cross-source deduplication using normalized DOI, arXiv ID, and SHA-256 title hash.
- Preservation of cross-source references in `source_refs_json`.
- Title-hash, source-reference, and supporting indexes for the new deduplication path.

### Changed
- Provider refreshes now merge source metadata instead of replacing the paper with a second ID.
- Manual tags remain separate from provider-derived tags and survive refreshes.
- Tag filtering searches both manual and source-derived tags.
- README reorganized around current release, workflow, UI, upgrades, and roadmap.

### Compatibility
- Existing v0.4.x SQLite databases are migrated additively. No reset is required.
- Existing manual tag commands remain supported.

### Testing focus
- Duplicate detection by DOI, arXiv ID, and punctuation/case-insensitive title hash.
- Cross-source reference merging.
- Source-tag persistence and tag filtering.
- TUI controls/count/detail rendering.
- CLI library count behavior.

## 0.4.4 — 2026-10-08

### Fixed
- Fixed Textual UI tests to use `App.run_test()` and the real compose/mount lifecycle.

### Changed
- Added `pytest-asyncio` for async Textual tests.
- CI UI job installs the complete development test environment.

## 0.4.3 — 2026-10-07

### Added
- TUI `?` help overlay with keyboard/action reference.
- TUI sort selector with relevance, publication date newest/oldest, newest added, title A–Z, and citation count.
- TUI `S` hotkey to focus sorting.
- TUI `G` tag editor with current tags and existing-tag suggestions.
- TUI `L` hotkey to save the selected paper for offline use.
- CLI tag editing modes: add, `--remove`, and `--set`.
- SQLite `set_tags()`, `remove_tags()`, and `all_tags()` helpers.
- New deterministic tie-breakers for list ordering.
- Background thread worker for TUI offline PDF downloads.
- GitHub Actions UI test job with Textual installed.
- Indexes for case-insensitive title ordering and citation sorting.
- Additional public sort option: `citations` and `published_oldest`.

### Changed
- TUI details now refresh after tag/offline actions.
- Tag normalization is centralized in the storage layer.
- TUI workflow help is visible without opening README or a shell.

### Compatibility
- Existing v0.4.x SQLite libraries remain usable; no reset required.
- Existing tag-add syntax remains valid: `python cli.py tags 42 tag-a tag-b`.

### Testing focus
- Sorting behavior and deterministic ordering.
- Tag add/remove/replace persistence.
- CLI parser coverage for new options.
- TUI import remains optional and skipped when Textual is not installed.

## 0.4.2 — 2026-10-06

### Fixed
- CI/test import path reliability via `pyproject.toml` `pythonpath` configuration.

### Changed
- Bulk SQLite upsert path uses one transaction.
- Added database indexes for title and DOI lookup.
- Added batch sizing for embedding inference.

## 0.4.1 — offline and bibliography

- Added BibTeX export and offline paper bundles with metadata, abstract, notes, and available PDFs.

## 0.4.0 — research inbox

- Added persistent reading statuses, dismiss/restore workflow, notes, tags, quick review, and the first Textual TUI.

## 0.3 — experimental LLM triage

- Added optional LLM assessment for relevance and potential overlap.

## 0.2 — semantic ranking

- Added embedding-based semantic relevance scoring.

## 0.1 — initial MVP

- Added OpenAlex, Semantic Scholar, and arXiv fetching, SQLite storage, and keyword ranking.
