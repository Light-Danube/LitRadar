# LitRadar v0.4

A small personal literature radar and research inbox for tracking papers relevant to a configurable research profile.

The project evolves in place so the SQLite library survives upgrades:

- **v0.1** — source fetching + SQLite + keyword scoring.
- **v0.2** — semantic relevance with sentence-transformer embeddings.
- **v0.3** — optional LLM triage for relevance and *potential overlap*.
- **v0.4** — user-friendly research inbox: browsing, filtering, workflow status, dismiss/restore, notes/tags, quick review, and optional Textual TUI.

The goal is not to let an LLM decide what is novel. The goal is to reduce literature-search friction and keep a manageable, persistent reading queue.

## Architecture

```text
sources/
├── openalex.py
├── semantic_scholar.py
└── arxiv.py

ranking/
├── keywords.py
├── embeddings.py
└── scoring.py

storage/
└── sqlite.py

llm/
├── assessment.py
└── providers.py

cli.py
ui.py
ui.tcss
```

```text
OpenAlex / Semantic Scholar / arXiv
                 ↓
           metadata fetch
                 ↓
              SQLite
                 ↓
       keyword + semantic score
                 ↓
           Research Inbox
        ↙        ↓         ↘
   filters    workflow     details
                ↓
       optional LLM triage
```

## Requirements

Python 3.10+ is supported by the codebase. Python 3.11 or 3.12 is a safe default for ML environments; PyTorch availability can vary by Python version/platform.

### Core installation

```bash
python -m venv .venv
```

Activate the environment.

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows CMD:**

```cmd
.venv\Scripts\activate
```

**Linux/macOS:**

```bash
source .venv/bin/activate
```

Install core dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt  # optional, for tests
python -m pip install -r requirements-llm.txt  # optional, for LLM providers
```

The Textual UI is optional:

```bash
python -m pip install -r requirements-ui.txt
```

### First run

Initialize or migrate the database:

```bash
python cli.py init
```

Check the command list before doing anything else:

```bash
python cli.py --help
```

Every command has its own help:

```bash
python cli.py list --help
python cli.py search --help
python cli.py review --help
python cli.py ui --help
```

Run the offline fixture first:

```bash
python cli.py ingest-fixture data/fixture.json
python cli.py list
```

For a keyword-only troubleshooting run:

```bash
python cli.py ingest-fixture data/fixture.json --no-semantic
```

## v0.4 Research Inbox

### Browse the stored literature

```bash
python cli.py list
python cli.py list --limit 100
python cli.py list --status new
python cli.py list --status to-read
python cli.py list --status read
python cli.py list --status dismissed
```

Search and filter:

```bash
python cli.py list --query "context selection"
python cli.py list --tag sarcasm
python cli.py list --min-score 0.80
python cli.py list --status new --sort recent
python cli.py list --sort newest_added
```

Show a specific paper:

```bash
python cli.py show 42
```

Get a compact library overview:

```bash
python cli.py stats
```

### Reading workflow

LitRadar v0.4 uses persistent workflow states:

```text
new → to-read → read → archived
 \_____________________↘
          dismissed
```

Change status:

```bash
python cli.py set-status 42 to-read
python cli.py set-status 42 read
python cli.py set-status 42 archived
```

Dismiss without deleting:

```bash
python cli.py dismiss 42 --reason irrelevant
```

Allowed reasons are `irrelevant`, `duplicate`, `too broad`, `wrong domain`, `already known`, and `other`.

Restore:

```bash
python cli.py restore 42
python cli.py restore 42 --status to-read
```

Add tags and notes:

```bash
python cli.py tags 42 context-selection sarcasm
python cli.py note 42 "Useful baseline, but their context selector is not task-specific."
```

Open the stored URL in your default browser:

```bash
python cli.py open 42
```

### Quick review

For fast triage without starting the full UI:

```bash
python cli.py review
```

Keyboard actions:

```text
t  → to-read
r  → read
d  → dismiss
s  → skip
o  → open in browser
q  → quit
```

### Textual UI

Install the optional dependency:

```bash
python -m pip install -r requirements-ui.txt
```

Launch:

```bash
python cli.py ui
```

The UI provides a searchable table, status filtering, a details pane, and keyboard actions for the basic workflow.

Keys:

```text
↑ / ↓  select paper
Enter  table selection
T      to-read
R      read
D      dismiss
U      restore to new
O      open URL
/      focus search
F      focus status filter
Q      quit
```

Textual is deliberately optional so the core CLI remains usable on a minimal Python installation.

## v0.2 semantic scoring

v0.2 combines:

```text
final = keyword_weight * keyword_score
      + semantic_weight * semantic_score
```

The default weights are 0.35 keyword / 0.65 semantic.

Semantic scoring uses `all-MiniLM-L6-v2` by default. The model is loaded lazily.

## v0.3 LLM assessment

LLM assessment remains **experimental/advisory** in v0.4. It should not be treated as a novelty detector or an authoritative literature-review decision.

The command is available as:

```bash
python cli.py assess --provider ollama --model llama3.1:8b --limit 5
```

The assessment stores structured fields such as:

- relevance;
- potential overlap;
- overlap level;
- summary;
- fit reason;
- overlap reason;
- suggested tags.

At this stage, the primary library ranking does **not** depend on the LLM assessment.

## Research profile

Edit `research_profile.json` rather than changing Python code.

The profile contains:

- a natural-language research description used by semantic scoring and LLM assessment;
- weighted keyword groups;
- keyword/semantic score weights;
- the embedding model name.

## Database, migration, and upgrades

The default database is:

```text
data/litradar.sqlite3
```

**Do not delete this file when upgrading.**

LitRadar automatically migrates missing columns and indexes on startup.

User workflow data is preserved when the same paper is fetched again. Source refreshes update metadata and scores but intentionally keep:

- status;
- tags;
- notes;
- read/archive/dismiss timestamps;
- dismiss reason;
- stored LLM assessment.

### Recommended upgrade workflow

When a new LitRadar release is downloaded or pulled from Git:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-llm.txt
python -m pip install -r requirements-ui.txt
python cli.py init
pytest -q
```

No database recreation is required.

## GitHub / GitHub Desktop

LitRadar is designed to be kept as a normal Git repository. Keep the code under version control, but keep the local SQLite database and secrets out of Git.

The included `.gitignore` excludes:

```text
data/*.sqlite3
.venv/
.env
Python caches
IDE metadata
```

`research_profile.json` is intentionally tracked so the research configuration can evolve with the project.

### Create the repository with GitHub Desktop

1. Extract/copy the LitRadar project folder to a permanent location.
2. Open **GitHub Desktop**.
3. Choose **File → Add local repository…**.
4. Select the LitRadar folder. If GitHub Desktop says it is not a repository, choose **Create a Repository** from the same screen.
5. Set the repository name, e.g. `LitRadar`.
6. Review the initial changed files. Confirm that `data/litradar.sqlite3`, `.env`, and `.venv` are ignored.
7. Enter an initial commit message such as `Initial LitRadar v0.4.0` and click **Commit to main**.
8. Click **Publish repository** in GitHub Desktop and choose the GitHub account/visibility you want.

### After publication

When LitRadar gets a new version:

1. Back up the folder (or simply rely on Git history plus a separate DB backup).
2. In GitHub Desktop, use **Fetch origin** and then **Pull origin**.
3. If dependencies changed, run the relevant `pip install -r ...` commands from the upgrade section.
4. Run `python cli.py init` to apply database migrations.
5. Run `pytest -q`.

Your `data/litradar.sqlite3` remains local and is not overwritten by a normal Git pull because it is ignored.

### Recommended repository hygiene

Do not commit API keys, `.env`, or the SQLite database. If the research profile ever becomes private or contains personal notes, move those values to a separate local file and ignore it.

A useful first repository layout after the initial commit is:

```text
LitRadar/
├── cli.py
├── ui.py
├── ui.tcss
├── research_profile.json
├── requirements*.txt
├── sources/
├── ranking/
├── storage/
├── llm/
├── tests/
├── data/
│   └── fixture.json
└── README.md
```

## Development and tests

Run the full test suite:

```bash
pytest -q
```

The UI dependency is optional. Tests that require Textual are skipped when Textual is not installed.

The core test suite covers storage, migration, ranking, CLI behavior, semantic ranking, and LLM assessment parsing/storage.
