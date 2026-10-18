# Changelog

## 1.0.0 — GitHub Release

LitBeacon 1.0 brings the browser, CLI and optional Textual/Telegram workflows together in a local research workspace. Since v0.8.0, the candidate adds venue search and evidence worksheets, citation-map and annotation improvements, consistent library backup and new-destination restore, keyboard and error-handling fixes. Optional local semantic exploration stays off by default. Existing LitRadar module, data and configuration identifiers remain compatible.

Windows source-ZIP setup now selects Python 3.12/3.11, preserves an incompatible `.venv`, installs normal web/TUI dependencies without optional PDF/BibTeX parsers, and avoids pip-cache permission failures. The user reported successful standard-user source-ZIP setup and a separately built 1.0 two-file setup-ZIP install with the web workspace showing v1.0.0. At tagged commit `da4486ab`, Linux Python 3.12 package smoke and **740 Python / 48 JavaScript** local tests passed. The exact wheel on the [v1.0.0 GitHub Release](https://github.com/Light-Danube/LitRadar/releases/tag/v1.0.0) passed a fresh Linux Python 3.12 install, `pip check`, packaged web edit/restart and backup/restore smoke on 2026-10-18. The uploaded `SETUP.txt` still needs replacement with corrected direct-download wording and the Windows pip-cache workaround. Native macOS installation and same-commit hosted CI remain unverified; GitHub Actions jobs cannot start because of account billing.

[Installation](docs/PACKAGE-SETUP.md) · [user guide](docs/USER-GUIDE.md) · [release checklist](docs/LOCAL-1.0-RELEASE-CHECKLIST.md) · [development patch notes and prior release history](docs/archive/release-1.0/CHANGELOG-development.md)

## 0.8.0 and earlier

The v0.8.0 release notes and earlier version history are preserved in the [development changelog archive](docs/archive/release-1.0/CHANGELOG-development.md#080--litbeacon-browser-research-workspace--2026-10-12).
