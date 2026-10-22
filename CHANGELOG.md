# Changelog

## Post-1.0 — proposed Draft PR

Add a separate opt-in local bibliography workflow in CLI and EN/UK Inbox UI. Preview selected RIS/BibTeX/PDF Info metadata before confirming new paper records or duplicate provenance observations. Preserve existing metadata and user data, reject unsafe CLI input paths, keep import offline, and include additive batch/observation tables in existing SQLite backups. PDF is metadata-only; no OCR, original-file copy, automatic undo or provider adapter. See the [EN/UK guide](docs/research/local-bibliography-import.md). No version, tag or release change.

Previously merged: add opt-in OpenAlex metadata-language filtering (`any`/`uk`/`en`) in broad CLI and venue CLI/Research search, with explicit unsupported-provider errors, separate filtered caches and retained language provenance. Defaults remain unfiltered. Add an optional UK/EN keyword profile, canonical Unicode keyword normalization and EN/UK explanations that metadata language does not guarantee full-text language. That increment introduced no provider or bibliography importer. See the [guide](docs/research/metadata-language-search.md).

## 1.0.0 — GitHub Release

LitBeacon 1.0 brings the browser, CLI and optional Textual/Telegram workflows together in a local research workspace. Since v0.8.0, the candidate adds venue search and evidence worksheets, citation-map and annotation improvements, consistent library backup and new-destination restore, keyboard and error-handling fixes. Optional local semantic exploration stays off by default. Existing LitRadar module, data and configuration identifiers remain compatible.

Windows source-ZIP setup now selects Python 3.12/3.11, preserves an incompatible `.venv`, installs normal web/TUI dependencies without optional PDF/BibTeX parsers, and avoids pip-cache permission failures. The user reported successful standard-user source-ZIP setup and a separately built 1.0 two-file setup-ZIP install with the web workspace showing v1.0.0. At tagged commit `da4486ab`, Linux Python 3.12 package smoke and **740 Python / 48 JavaScript** local tests passed. The exact wheel on the [v1.0.0 GitHub Release](https://github.com/Light-Danube/LitRadar/releases/tag/v1.0.0) passed a fresh Linux Python 3.12 install, `pip check`, packaged web edit/restart and backup/restore smoke on 2026-10-18. The public `SETUP.txt` now has corrected direct-download instructions, the Windows pip-cache workaround and the MIT notice; its downloaded SHA-256 matches the prepared file. Native macOS installation and same-commit hosted CI remain unverified; GitHub Actions jobs cannot start because of account billing.

[Installation](docs/PACKAGE-SETUP.md) · [user guide](docs/USER-GUIDE.md) · [release checklist](docs/archive/release-1.0/RELEASE-CHECKLIST-1.0.md) · [development patch notes and prior release history](docs/archive/release-1.0/CHANGELOG-development.md)

## 0.8.0 and earlier

The v0.8.0 release notes and earlier version history are preserved in the [development changelog archive](docs/archive/release-1.0/CHANGELOG-development.md#080--litbeacon-browser-research-workspace--2026-10-12).
