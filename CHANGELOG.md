# Changelog

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
