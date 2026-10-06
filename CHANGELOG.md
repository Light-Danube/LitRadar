# Changelog

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
- `review` command for keyboard-driven terminal triage without the full UI.
- Optional Textual TUI via `python cli.py ui`.
- Automatic SQLite migration from v0.1–v0.3 schemas.
- User workflow fields are preserved when an existing paper is refreshed from external sources.
- GitHub/GitHub Desktop setup and update instructions in README.

### Changed
- LLM assessment is now explicitly documented as experimental/advisory and is not presented as a novelty detector.
- Search-source refreshes no longer reset a paper's workflow status, tags, notes, or reading timestamps.
