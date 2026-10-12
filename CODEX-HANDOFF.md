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

## Suggested next Codex task

Add review/edit/history UI around stored annotations, preserving note revisions and legacy workflows. Alternatively continue graph year filters/exports or start externalizing UI strings for Ukrainian localization. Keep automatic imports and generated suggestions explicit and opt-in; never silently overwrite personal notes.

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
