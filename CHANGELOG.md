# Changelog

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
