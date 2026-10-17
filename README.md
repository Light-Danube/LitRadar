# LitBeacon Research Workspace

**LitBeacon** is a local-first workspace for discovering, ranking, reading and comparing academic papers. It keeps your library, notes and research history in SQLite and offers a browser interface, CLI, Textual TUI and optional Telegram workflows.

The project was formerly **LitRadar**. Existing module names, database paths, `LITRADAR_*` configuration and Windows task identifiers remain compatible.

## Release status

**Released: v0.8.0** — local browser workspace, citation map, heuristic literature clusters, editable annotations and scheduled-job controls.

**Draft v1.0.0 candidate:** graph and annotation refinements, optional local semantic exploration, and venue discovery/evidence worksheets in the CLI and Research browser section. The branch is for installation testing; no 1.0 release has been published. See the [changelog](CHANGELOG.md).

Feature development is frozen for local-only 1.0. Gates 1–5 are complete for the bounded candidate; the [release checklist](docs/LOCAL-1.0-RELEASE-CHECKLIST.md) tracks remaining Gate 6 checks. Hosted Actions are deferred by user choice while account billing blocks job startup.

## Quick start

Use **Python 3.11 or newer** (3.12 recommended). A published `LitBeacon-<version>-setup.zip` needs only its wheel and `SETUP.txt`; extract it into a fresh folder. The [Windows, macOS and Linux installation guide](docs/PACKAGE-SETUP.md) also explains how to build the unpublished 1.0 candidate for testing. Installation downloads dependencies; local library use needs no cloud service.

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

The current cloud venue probe was blocked by proxy 403; live verification stays pending. The user reported successful CLI retrieval on their installation.

```sh
python cli.py evidence show PAPER_ID
python cli.py evidence export PAPER_ID --output matrix.md
```

Replace `PAPER_ID` with a canonical library ID. Worksheets are human-editable, preserve per-field provenance and remain separate from personal notes. No LLM is required. [Full usage, JSON edits, CSV export, bounds and recovery](docs/research/venue-discovery.md).

## Data and limitations

Source checkouts keep `data/litradar.sqlite3`; installed wheels use a separate writable per-user LitBeacon directory ([locations/override](docs/USER-GUIDE.md#wheel-installation)). Migrations are additive. Unreleased `library-backup` creates a consistent SQLite snapshot with explicitly elected files; `library-restore` verifies it into a new directory. [Backup, exclusions and upgrade instructions](docs/USER-GUIDE.md#consistent-local-backup-and-restore-unreleased).

Discovery indexes, preprints, venue metadata and citations do not certify peer review, Scopus/WoS membership or academic novelty. Missing evidence stays unverified. The user confirmed live CLI retrieval locally; cloud OpenAlex/Crossref probes were blocked by proxy **403**. Synthetic tests establish behavior, not live coverage. Windows, rendered-browser and real-model results are tracked separately in the validation documents.

## Documentation

- [Setup and updates](docs/PACKAGE-SETUP.md) · [user guide and backup/restore](docs/USER-GUIDE.md) · [environment template](.env.example)
- [Research browser](docs/research/web-workspace.md) · [venue discovery and evidence](docs/research/venue-discovery.md) · [CLI scenario (RU)](docs/research/cli-workflow-ru.md)
- [Annotations and recovery](docs/V08-ANNOTATION-WORKFLOWS.md) · [semantic exploration limits](docs/SEMANTIC-WORKSPACE.md)
- [Network use](docs/NETWORK-USE.md) · [Telegram troubleshooting](docs/TELEGRAM-TROUBLESHOOTING.md) · [local logs](docs/LOGGING.md) · [optional Docker deployment](DOCKER.md)
