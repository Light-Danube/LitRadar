## 0.4.4 — UI test lifecycle fix

- Fixed Textual UI test to run through `App.run_test()` and the real compose/mount lifecycle.
- Added `pytest-asyncio` to development dependencies.
- Updated GitHub Actions UI job to install the complete development test environment.
- Removed the invalid direct `list(app.compose())` test pattern that raises `NoActiveAppError` on current Textual releases.

# Changelog

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
