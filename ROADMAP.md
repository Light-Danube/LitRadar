# LitBeacon Research Workspace — Roadmap

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

- [x] Add graph pan/zoom, keyboard/click node selection, directional arrows/legend, relation/provider filters applied before bounded traversal, and merged edge provenance (unreleased).
- [ ] Improve graph layout, add year filters, and export to SVG/GraphML/JSON.
- [ ] Add provenance-aware annotations: distinguish user notes, imported notes, extracted metadata, and generated suggestions; record timestamps and optional source references.
- [ ] Add semantic-similarity edges and embedding-based clustering only behind an explicit optional dependency/feature flag, with fixtures and evaluation against real-but-shareable small corpora.
- [ ] Test graph edge direction and deduplication more extensively against mixed OpenAlex/Semantic Scholar records.
- [ ] Add UI workflow smoke tests for inbox editing, clusters, and graph navigation; verify on Windows.
- [ ] Refine onboarding, keyboard navigation, empty/loading/error states, and accessibility contrast.

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
