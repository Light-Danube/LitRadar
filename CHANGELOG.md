# Changelog

## 1.0.0 — tagged, GitHub Release pending

LitBeacon 1.0 brings the browser, CLI and optional Textual/Telegram workflows together in a local research workspace. Since v0.8.0, the candidate adds venue search and evidence worksheets, citation-map and annotation improvements, consistent library backup and new-destination restore, keyboard and error-handling fixes, and a small two-file wheel/setup ZIP. Optional local semantic exploration stays off by default. Existing LitRadar module, data and configuration identifiers remain compatible.

Windows source-ZIP setup now selects Python 3.12/3.11, preserves an incompatible `.venv`, installs normal web/TUI dependencies without optional PDF/BibTeX parsers, and avoids pip-cache permission failures. The user reported successful standard-user source-ZIP setup and a separate 1.0 two-file setup-ZIP install with the web workspace showing v1.0.0. At tagged commit `da4486ab`, Linux Python 3.12 package smoke and **740 Python / 48 JavaScript** local tests passed. Native macOS installation and same-commit hosted CI remain unverified; GitHub Actions jobs cannot start because of account billing. **The `v1.0.0` tag exists, but no GitHub Release or setup asset is published.**

[Installation](docs/PACKAGE-SETUP.md) · [user guide](docs/USER-GUIDE.md) · [release checklist](docs/LOCAL-1.0-RELEASE-CHECKLIST.md) · [development patch notes and prior release history](docs/archive/release-1.0/CHANGELOG-development.md)

## 0.8.0 and earlier

Published v0.8.0 is the current release. Its release notes and earlier version history are preserved in the [development changelog archive](docs/archive/release-1.0/CHANGELOG-development.md#080--litbeacon-browser-research-workspace--2026-10-12).
