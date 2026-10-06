# LitRadar 0.4.2

## CI reliability and scaling groundwork

- Added `pyproject.toml` with pytest repository-root path configuration, fixing CI import failures such as `ModuleNotFoundError: No module named 'cli'`.
- Added explicit indexes for normalized title and case-insensitive DOI lookups.
- Added transactional `PaperStore.upsert_papers()` and switched bulk ingestion to one transaction instead of one commit per paper.
- Added configurable embedding inference batch size (default 32).
- Added regression tests for project import configuration and batch storage/indexes.

## Technical debt noted for future versions

- Library text search uses `%LIKE%` over title/abstract/venue; SQLite FTS5 is the likely next step for large libraries.
- Tags are stored as JSON and filtered with `LIKE`; a normalized many-to-many tag table is preferable at larger scale.
- Source requests are currently sequential; concurrency should be introduced carefully because API rate limits differ by source.
- Full-library semantic rescoring will eventually require chunked/streaming ranking rather than holding every embedding in memory.
- Large BibTeX export currently materializes a large row set; streaming export can follow when needed.
# Changelog

## v0.4.1 — Offline & Bibliography Convenience Patch

### Added
- `export-bibtex` command for a single paper or a workflow status view.
- `download` command for offline bundles with metadata, abstract, notes, BibTeX, and an available PDF.
- `open` prefers a locally saved PDF when one exists.
- Semantic Scholar requests open-access PDF metadata when available.
- Offline storage under `data/offline/` is ignored by Git.
- README documents the v0.4.0 → v0.4.1 update path and future v0.5 personalization direction.

### Compatibility
- No database reset is required.
- Existing status, tags, notes, scores, and LLM assessments are preserved.

## v0.4.0 — Research Inbox

### Added
- GitHub Actions CI workflow running the core test suite on Python 3.11 and 3.12.
- Friendly root `--help` with examples and per-command help.
- `list` command for browsing the stored literature with status, text, tag, score, and sort filters.
- Workflow statuses: `new`, `to-read`, `read`, `archived`, `dismissed`.
- `set-status`, `dismiss`, and `restore` commands.
- Persistent paper tags and notes.
- `stats` command for a quick library overview.
- `open` command for opening a paper URL in the default browser.
- `review` command for terminal triage.
- Optional Textual TUI via `python cli.py ui`.
- Automatic SQLite migration from v0.1–v0.3 schemas.
- Workflow fields are preserved when an existing paper is refreshed from external sources.
- GitHub/GitHub Desktop setup and update instructions in README.

### Changed
- LLM assessment is explicitly experimental/advisory and is not presented as a novelty detector.
- Search refreshes no longer reset workflow status, tags, notes, or reading timestamps.
