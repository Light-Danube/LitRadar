# LitBeacon Research Workspace

**LitBeacon** is a local-first workspace for discovering, ranking, reading and comparing academic papers. It keeps your library, notes and research history in SQLite and offers a browser interface, CLI, Textual TUI and optional Telegram workflows.

The project was formerly **LitRadar**. Existing module names, database paths, `LITRADAR_*` configuration and Windows task identifiers remain compatible.

## Release status

**Released: v0.8.0** — local browser workspace, citation map, heuristic literature clusters, editable annotations and scheduled-job controls.

**Unreleased:** graph and annotation refinements, optional local semantic exploration, and venue discovery/evidence worksheets in the CLI and Research browser section. The release version stays 0.8.0 while validation gates remain open. See [CHANGELOG](CHANGELOG.md) and the [Gate 1 history archive](docs/archive/gate1/README.md).

Feature development is frozen for local-only 1.0. Gate 1 is complete; the [active release checklist](docs/LOCAL-1.0-RELEASE-CHECKLIST.md) tracks recovery verification and the remaining release gates.

## Quick start

Use **Python 3.11 or newer**. For releases providing `LitBeacon-<version>-setup.zip`, extract it and follow the short `SETUP.txt`: only the runtime wheel and guide are needed. [Package setup and updates](docs/PACKAGE-SETUP.md). Installation downloads dependencies; local library use needs no cloud service.

The source-checkout commands below are for developers and existing launcher users.

### Windows launchers

Run `run_web.bat` for the browser workspace, `run_litradar.bat` for the TUI, or `run_cli.bat` for a persistent CLI shell. Launchers create `.venv`, install dependencies and initialize the existing database.

The shared Windows setup installs the full dependency sets, including optional semantic and browser-test packages. For a lighter installation, use the manual setup below. [Launcher and update details](docs/USER-GUIDE.md#start-here).

### Manual setup

Create and activate a virtual environment:

```sh
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```sh
source .venv/bin/activate
```

Install the lightweight core plus browser dependencies and start the workspace:

```sh
python -m pip install ".[web]"
python cli.py init
python cli.py web
```

Open **http://127.0.0.1:8765**. The server binds to localhost; it has no account/authentication layer. Use `python cli.py web --port 8787` if the default port is occupied.

For CLI only, install `python -m pip install .`; for the TUI, install `python -m pip install ".[ui]"` and run `python cli.py ui`. Unlike the package core, legacy `requirements.txt` also installs sentence-transformers. [Optional dependencies and configuration](docs/USER-GUIDE.md#installation).

Try the library without scholarly API access:

```sh
python cli.py ingest-fixture data/fixture.json --no-semantic
python cli.py list
python cli.py --help
```

## Main workflows

- **Discover papers:** broad OpenAlex, Semantic Scholar and arXiv searches, source progress, cached results and conservative deduplication.
- **Organize reading:** search/filter the inbox, edit notes/tags/status, record relevance feedback and export Markdown or BibTeX.
- **Explore connections:** bounded citation and related-work maps with provider provenance, filters and SVG/GraphML/JSON export.
- **Use the browser:** English/Ukrainian interface, System/Light/Dark appearance, keyboard navigation and draft-preserving editors.
- **Retain evidence:** separate annotations with provenance, revision history and guarded recovery; optional bounded file imports.
- **Work offline or on a schedule:** local reading bundles, legal open-access PDF downloads, research digests and optional Telegram delivery.

[Detailed workflows, commands and shortcuts](docs/USER-GUIDE.md). Optional LLM assessment is advisory and requires an explicit action. Local semantic graph exploration is off by default and requires an existing local model; [setup and evaluation limits](docs/SEMANTIC-WORKSPACE.md).

## Venue search and evidence worksheet (unreleased)

Look up a venue, inspect its identity, then search a concrete OpenAlex source ID:

```sh
python cli.py venue lookup "Computational Linguistics" --limit 10
python cli.py venue search SOURCE_ID "emotion context" --year-from 2023 --year-to 2026 --limit 20
```

Replace `SOURCE_ID` with the returned `S` + digits identifier. Searches use structured source/year filters and bounded pages. Returned paper IDs appear in the Literature inbox. The **Research** section provides venue search, editable evidence and quick-topic templates; [browser workflow and saved results](docs/research/web-workspace.md).

[Independent venue verification](docs/archive/gate1/research/venue-verification.md) records transport/integrity tests and a repeatable public probe. The current cloud probe was blocked by proxy 403; live verification stays pending.

```sh
python cli.py evidence show PAPER_ID
python cli.py evidence export PAPER_ID --output matrix.md
```

Replace `PAPER_ID` with a canonical library ID. Worksheets are human-editable, preserve per-field provenance and remain separate from personal notes. No LLM is required. [Full usage, JSON edits, CSV export, bounds and recovery](docs/research/venue-discovery.md).

## Data and limitations

Source checkouts keep `data/litradar.sqlite3`; installed wheels use a separate writable per-user LitBeacon directory ([locations/override](docs/USER-GUIDE.md#wheel-installation)). Migrations are additive. Unreleased `library-backup` creates a consistent SQLite snapshot with explicitly elected files; `library-restore` verifies it into a new directory. [Backup, exclusions and upgrade instructions](docs/USER-GUIDE.md#consistent-local-backup-and-restore-unreleased).

Discovery indexes, preprints, venue metadata and citations do not certify peer review, Scopus/WoS membership or academic novelty. Missing evidence stays unverified. The user confirmed live CLI retrieval locally; cloud OpenAlex/Crossref probes were blocked by proxy **403**. Synthetic tests establish behavior, not live coverage. Windows, rendered-browser and real-model results are tracked separately in the validation documents.

## Documentation

- [User guide and configuration](docs/USER-GUIDE.md) · [environment template](.env.example) · [Telegram diagnostics](docs/TELEGRAM-TROUBLESHOOTING.md)
- [Краткий CLI-сценарий (RU)](docs/research/cli-workflow-ru.md) · [Venue discovery and evidence](docs/research/venue-discovery.md) · [literature comparison and verification limits](docs/archive/gate1/research/erc-context-novelty-matrix-2026.md)
- [Annotations and recovery](docs/V08-ANNOTATION-WORKFLOWS.md) · [semantic exploration](docs/SEMANTIC-WORKSPACE.md)
- [Docker deployment](DOCKER.md) · [isolated development](docs/ISOLATED-DEV.md)
- [Development and CI](docs/USER-GUIDE.md#development-and-ci) · [agent rules](AGENTS.md) · [handoff](CODEX-HANDOFF.md)
- [Roadmap](ROADMAP.md) · [changelog](CHANGELOG.md) · [Gate 1 design, research and validation archive](docs/archive/gate1/README.md)
