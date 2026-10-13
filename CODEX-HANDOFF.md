# Codex development handoff — LitBeacon Research Workspace

This file records development progress and a safe starting point for continuing with Codex. The repository is still named `LitRadar` on GitHub, while the public-facing application name is **LitBeacon**.

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
