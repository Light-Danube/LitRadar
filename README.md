# LitBeacon Research Workspace

**LitBeacon** is a local-first workspace for discovering, reading and comparing academic papers. It keeps your library, notes and research history in SQLite, with a browser interface, CLI, Textual TUI and optional Telegram workflows. The project was formerly LitRadar; existing module names, data paths and `LITRADAR_*` settings remain compatible.

## Release status

**Published release: v0.8.0.** Source `main` contains an **unreleased v1.0.0 candidate**; no 1.0 setup ZIP has been published. Feature development is frozen. Gates 1–5 are complete for this bounded candidate; [Gate 6 checks and limits](docs/LOCAL-1.0-RELEASE-CHECKLIST.md) remain open. Hosted Actions are deferred because account billing prevents jobs from starting.

## Start on Windows from GitHub's source ZIP

1. Install **Python 3.12** from [python.org](https://www.python.org/downloads/windows/) with the Windows `py` launcher. Python 3.12.7 works; check `py -3.12 --version` in PowerShell.
2. Use **Code → Download ZIP**, extract it into a new writable folder, and open the folder containing `run_litbeacon_web.bat`.
3. Run `run_litbeacon_web.bat`; it creates `.venv`, installs web and TUI dependencies and starts the local web workspace. Open <http://127.0.0.1:8765>.

If an old `.venv` uses a different Python, the launcher keeps it as `.venv-before-python312` and creates a fresh one; your library remains separate. The [step-by-step Windows source-ZIP guide](docs/WINDOWS-SOURCE-ZIP.md) covers a separate trial data folder and errors. The **future release download** is a smaller, two-file setup ZIP with a wheel and `SETUP.txt`; follow the [Windows, macOS and Linux package guide](docs/PACKAGE-SETUP.md) for that route. Dependency installation needs internet access; saved-library work is local.

## Use the workspace

The browser, CLI and TUI support discovery, notes and tags, citation maps, annotations, Research venue search and evidence worksheets, local exports and recovery. Provider searches use the network; optional LLM and local semantic exploration require explicit setup. The web server binds to localhost and has no authentication for public/LAN hosting.

For a source checkout, run `run_litbeacon_cli.bat` or `run_litbeacon.bat` on Windows for the CLI/TUI. On macOS/Linux, follow the [package guide](docs/PACKAGE-SETUP.md) or the [source setup and command reference](docs/USER-GUIDE.md). Previous `litradar` launcher names remain aliases.

Installed wheels keep data in a writable per-user LitBeacon directory; source checkouts use `data/litradar.sqlite3` unless configured otherwise. An install never moves an old library automatically. [Back up and upgrade safely](docs/USER-GUIDE.md#consistent-local-backup-and-restore-unreleased).

## Guides

- [Installation and updates](docs/PACKAGE-SETUP.md) · [Windows source ZIP](docs/WINDOWS-SOURCE-ZIP.md) · [user guide](docs/USER-GUIDE.md)
- [Research workflow](docs/research/web-workspace.md) · [venue/evidence details](docs/research/venue-discovery.md) · [network use](docs/NETWORK-USE.md)
- [Changelog](CHANGELOG.md) · [roadmap](ROADMAP.md) · [release checklist](docs/LOCAL-1.0-RELEASE-CHECKLIST.md)

Provider metadata and citation links do not prove peer review, indexing or novelty. See the guides for evidence limits and optional components.
