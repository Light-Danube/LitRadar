# LitBeacon

LitBeacon is a local research workspace for finding, reading and comparing academic papers. Your library, notes and research history live in SQLite on your computer. It includes a browser interface, CLI, optional Textual TUI and Telegram workflows. LitRadar module names and existing data/configuration paths remain compatible.

**Release status:** [v1.0.0](https://github.com/Light-Danube/LitRadar/releases/tag/v1.0.0) provides a wheel and `SETUP.txt`. [Release checks](docs/archive/release-1.0/RELEASE-CHECKLIST-1.0.md) track artifact and public-download verification.

## Start on Windows from GitHub's source ZIP

1. Install Python **3.12** from [python.org](https://www.python.org/downloads/windows/) with the `py` launcher. In PowerShell, check `py -3.12 --version`.
2. Choose **Code → Download ZIP**, extract it into a writable folder, then open the folder containing `run_litbeacon_web.bat`.
3. Run `run_litbeacon_web.bat` and open <http://127.0.0.1:8765>. Setup creates `.venv` and installs normal web/TUI dependencies; the first launch needs internet access.

For an isolated trial library, error help and updates, follow the [Windows source-ZIP guide](docs/WINDOWS-SOURCE-ZIP.md). The smaller release download consists of a wheel and `SETUP.txt`; see [Windows, macOS and Linux package setup](docs/PACKAGE-SETUP.md). The source ZIP and wheel use different launch commands.

## Use LitBeacon

The workspace supports paper discovery, notes and tags, citation maps, annotations, venue search, evidence worksheets, local exports and backup/restore. Provider searches need network access; saved-library work is local. Optional LLM and semantic features require deliberate setup. The web server listens on localhost and has no login for public or LAN hosting.

[User guide](docs/USER-GUIDE.md) · [backup and restore](docs/USER-GUIDE.md#consistent-local-backup-and-restore) · [network use](docs/NETWORK-USE.md) · [logging](docs/LOGGING.md) · [Telegram help](docs/TELEGRAM-TROUBLESHOOTING.md)

Post-1.0 draft: [OpenAlex metadata-language search / пошук за мовою метаданих](docs/research/metadata-language-search.md), with coverage limits and an optional UK/EN keyword profile.

**Українською:** [встановлення з пакета для Windows, macOS і Linux](docs/PACKAGE-SETUP.uk.md) · [встановлення з вихідного ZIP на Windows](docs/WINDOWS-SOURCE-ZIP.uk.md). The detailed reference guide remains in English; the browser interface offers Ukrainian.

[All guides](docs/README.md) · [Changelog](CHANGELOG.md) · [License](LICENSE)

Provider metadata and citation links do not prove peer review, indexing or scientific novelty.
