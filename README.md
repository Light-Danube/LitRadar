# LitRadar v0.5.4

Personal literature radar and research inbox for discovering, ranking, triaging, and keeping academic papers locally.

## Current release

**v0.5.4 — visible TUI progress and reliable Windows updater feedback.**

This is a maintenance release on top of v0.5.3, improving search visibility and Windows update diagnostics without changing the existing SQLite library format destructively.

This release keeps v0.4.x and v0.5.0 SQLite libraries compatible. No database reset is required.

### What is new

- **Search workflow:** visible per-source progress in CLI/TUI, online source search from inside TUI, and a summary of fetched/new/library totals.
- **Personalization:** optional feedback-based ranking, explicit Useful/Not relevant feedback, and explanations of which research-profile groups influenced the recommendation.
- **Configuration:** `.env`, registered providers, API keys, timeouts/retries/backoff, and cached source-query results.
- **Offline access:** verified PDF downloads, readable PDF filenames, and optional legal open-access fallback through Unpaywall (`UNPAYWALL_EMAIL`).
- **Notes and exports:** structured note template through `$EDITOR`/`VISUAL`, Markdown literature-notes export, and BibTeX export with normalized, collision-safe citekeys.
- **Search:** SQLite FTS5 indexes title, abstract, venue, and personal notes when supported; a `LIKE` fallback remains available.
- **Citation metadata:** displays reference count and, when supplied by the provider, influential citation count.
- **Maintenance:** Windows updater now keeps its console open and reports success/failure; ZIP installs are explicitly told that `update_litradar.bat` requires a Git checkout. The TUI keeps a durable multi-line progress panel for provider search, ranking, and saving. The Rich-style test now supports both style strings and `Style` objects.

The LLM assessment remains experimental/advisory; it does not override the primary ranking or establish scientific novelty.

## Start here

For the quickest first launch on Windows, run `run_litradar.bat` from the project folder. It creates `.venv`, installs runtime/TUI dependencies once per dependency marker, and opens the TUI. Use `run_litradar.ps1` in PowerShell or `./run_litradar.sh` on Linux/macOS.

To launch a CLI command through the same helper, pass arguments, for example `run_litradar.bat list --status to-read`.

```bash
python cli.py --help
python cli.py config
python cli.py init
python cli.py stats
python cli.py list --limit 50
python cli.py search "adaptive context emotion sarcasm"
python cli.py ui
```

Every command has its own help page:

```bash
python cli.py search --help
python cli.py list --help
python cli.py download --help
python cli.py export-notes --help
```

Run the fixture without network access:

```bash
python cli.py ingest-fixture data/fixture.json --no-semantic
python cli.py list
python -m pytest -q
```

After publishing the repository, update a Git checkout through GitHub Desktop (`Fetch origin` → `Pull origin`) or run `update_litradar.bat` on Windows / `./update_litradar.sh` on Linux/macOS. The updater refuses to pull over tracked local edits, updates dependencies, runs `init`, and executes tests. It does not replace the local database, `.env`, or offline PDFs. If you installed LitRadar by extracting/copying a ZIP, the updater cannot fetch code because that folder has no `.git` directory; apply a newer patch/full ZIP manually or clone the repository with GitHub Desktop.
## Installation

Create a virtual environment and install the core dependencies:

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Linux/macOS
# source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For development/tests:

```bash
python -m pip install -r requirements-dev.txt
```

For the optional TUI:

```bash
python -m pip install -r requirements-ui.txt
```

For optional LLM providers:

```bash
python -m pip install -r requirements-llm.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in the providers you use:

```text
LITRADAR_SOURCES=openalex,semantic_scholar,arxiv
LITRADAR_SOURCE_WORKERS=3
LITRADAR_SOURCE_TIMEOUT=20
LITRADAR_SOURCE_RETRIES=3
LITRADAR_SOURCE_BACKOFF=2
LITRADAR_SOURCE_CACHE_TTL=3600

OPENALEX_API_KEY=
SEMANTIC_SCHOLAR_API_KEY=

# Optional legal OA PDF fallback by DOI (Unpaywall requires a contact email)
UNPAYWALL_EMAIL=you@example.org

LITRADAR_PERSONALIZATION_ENABLED=true
LITRADAR_PERSONALIZATION_WEIGHT=0.20
LITRADAR_PERSONALIZATION_MIN_FEEDBACK=5
LITRADAR_PERSONALIZATION_SCAN_LIMIT=5000
```

Check the effective, secret-masked configuration with:

```bash
python cli.py config
```

### Source expansion

Sources are registered in `sources/registry.py`. The environment variable controls which registered providers run:

```text
LITRADAR_SOURCES=openalex,semantic_scholar,arxiv
```

Adding a future provider is intentionally isolated behind the `SourceDefinition` adapter interface. This means the core ranking/library workflow does not need to know provider-specific API details.

### API/rate-limit notes

LitRadar keeps provider requests conservative because these APIs have different limits and policies. Current OpenAlex documentation says API keys are required for normal production-scale use and recommends backoff for rate limits; the old pre-2026 "polite pool"/`mailto` mechanism is no longer the production path. Semantic Scholar recommends authenticated API keys and provides batch/bulk endpoints for high-volume work. LitRadar therefore limits concurrency, retries only transient failures, and caches repeated searches locally.

## Core workflow

### Discover and rank

```bash
python cli.py search "adaptive context emotion sarcasm"
python cli.py search "context selection" --sources openalex semantic_scholar arxiv --per-source 20
```

The default ranking combines keyword and semantic relevance. Semantic embeddings are optional at runtime; LitRadar falls back to keyword scoring if the embedding backend is unavailable.

Repeated identical source searches can be served from `data/source_cache/` for the configured TTL, reducing API usage while you iterate on queries.

### Browse the library

```bash
python cli.py list
python cli.py list --limit 100
python cli.py list --status new
python cli.py list --status to-read
python cli.py list --status read
python cli.py list --tag sarcasm
python cli.py list --sort recent
python cli.py list --sort title
python cli.py list --sort citations
python cli.py list --sort references
python cli.py list --sort influential_citations
python cli.py list --sort personalized
```

`list` intentionally keeps a default display limit of 50, while reporting the full matching count. Use `--limit` when you want more rows. Text search covers title, abstract, venue, and personal notes. SQLite FTS5 is used when available; otherwise LitRadar falls back to `LIKE` search.

### Read, dismiss, and tag

```bash
python cli.py set-status 42 to-read
python cli.py set-status 42 read
python cli.py dismiss 42 --reason irrelevant
python cli.py restore 42
python cli.py tags 42 sarcasm context-selection
python cli.py tags 42 --remove broad-topic
python cli.py tags 42 --set "context-selection,sarcasm,important"
python cli.py note 42 "Useful baseline for related work."
```

Manual tags survive provider refreshes. Source-derived tags are stored separately.

### Explicit feedback and personalized ranking

Workflow status is only a weak preference signal: `read` means you read a paper, not necessarily that you liked it. v0.5 therefore adds explicit feedback:

```bash
python cli.py feedback 42 positive --reason useful
python cli.py feedback 43 negative --reason not_relevant
python cli.py list --sort personalized --limit 20
```

The personal ranker combines explicit feedback with conservative implicit signals from `to-read`, `read`, `archived`, and dismissal reasons. Duplicate dismissals are treated as neutral rather than as a dislike signal.

Personalization is deliberately gated by `LITRADAR_PERSONALIZATION_MIN_FEEDBACK` (default: 5 effective paper-level interactions). Before enough evidence exists, the personalized sort is identical to the base relevance sort.

The ranker is transparent and lightweight rather than a trained black-box recommender. It learns preference **by keyword-group evidence**, not by assuming every manual tag is a positive topic preference. This avoids misinterpreting workflow tags such as `to-cite`, `review-later`, or `important` as semantic likes.

### Offline reading and bibliography

```bash
python cli.py download 42
python cli.py download --status to-read --limit 10
python cli.py open 42
python cli.py export-bibtex 42 --output paper.bib
python cli.py export-bibtex --status read --output read.bib
python cli.py note 42 --edit
python cli.py export-notes --status read --output literature_review_draft.md
```

Offline bundles live under `data/offline/` and can include metadata, abstract, notes, BibTeX, and an available PDF. PDF downloads try the provider's direct PDF URL first, then—only when `UNPAYWALL_EMAIL` is set and the paper has a DOI—Unpaywall's documented legal OA PDF locations. LitRadar never attempts to bypass a paywall. A downloaded file is accepted only if it starts with the `%PDF-` signature. The resolver is cached locally to avoid repeated requests.

PDFs are stored inside each paper's offline bundle with a readable name based on year, first author, and title. Metadata/abstract/citation/notes are saved even if no PDF can be found.

Use `python cli.py note 42 --edit` to open a structured Markdown template in the editor configured by `VISUAL` or `EDITOR` (Windows falls back to Notepad). `export-notes` assembles metadata, abstract, and personal notes into one Markdown draft; it is a working document, not a generated literature review.

## Textual TUI

Install the optional UI dependency:

```bash
python -m pip install -r requirements-ui.txt
python cli.py ui
```

The TUI is a fast research inbox rather than a full reference manager.

### Main controls

```text
↑ / ↓   select paper
Enter   select row
/       search
F       status filter
K       tag filter
S       sort
```

### Workflow

```text
T       To Read
R       Read
Y       useful / positive feedback
N       not relevant / negative feedback
D       Dismiss
U       Restore
G       edit tags
L       save offline
O       open local PDF / URL
I       open DOI link
Ctrl+Enter / Fetch papers   search enabled online providers inside the TUI
?       keyboard help
Q       quit
```

The online source search is separate from the local library filter and displays source progress plus fetched/new/library totals. Search terms are highlighted in the selected paper's abstract when they match the local library filter. The detail view includes citation, reference, and (when available) influential-citation counts.

The TUI also supports a `Personalized` sort. The displayed Score column changes to the current ranking score while the detail panel shows both the base and displayed scores.

Offline network work runs through a Textual worker so a slow PDF request does not block the main UI event loop.

## Automatic source tags

When available, LitRadar extracts lightweight subject/category metadata:

- OpenAlex keywords;
- Semantic Scholar fields of study;
- arXiv category identifiers.

These values participate in tag filtering without overwriting manually curated tags.

## Deduplication

LitRadar uses several conservative identifiers during import:

1. normalized DOI;
2. arXiv identifier, when available;
3. SHA-256 of a normalized title (`casefold + punctuation removed + whitespace normalized`).

When a match is found, the existing paper ID is updated and cross-source references are retained. Manual status, tags, notes, and workflow history are not replaced by provider refreshes.

This is intentionally conservative. It does not try to aggressively decide that two substantially different titles are the same study.

## LLM assessment

LLM assessment remains **experimental/advisory**. It does not decide scientific novelty and does not alter the primary ranking.

```bash
python cli.py assess --provider ollama --model llama3.1:8b --limit 5
```

Treat LLM output as another signal to inspect, not as an authoritative literature-review decision. A small local model may produce structured output without producing sufficiently useful explanations.

## Database and local data

The main database is:

```text
data/litradar.sqlite3
```

Additional local state:

```text
data/offline/       # saved papers/PDFs
data/source_cache/   # cached provider results
data/oa_cache/       # cached Unpaywall legal-OA resolutions
.env                 # secrets and local configuration
```

These are intentionally excluded from Git.

Additive SQLite migrations are applied automatically. Upgrading from v0.4.x does not require a database reset.

## Upgrading and releasing with GitHub Desktop

For a local Git checkout, the easiest Windows update path is `update_litradar.bat`; on Linux/macOS use `./update_litradar.sh`. These scripts refuse to pull over local changes, run a fast-forward-only pull, update dependencies, migrate the library, and run tests. If you prefer a GUI, use GitHub Desktop's **Fetch origin → Pull origin**, then run `python cli.py init` and `python -m pytest -q`.

To publish a release: update `VERSION`, `pyproject.toml`, and `CHANGELOG.md`; commit and push in GitHub Desktop; then create a GitHub Release using a matching tag such as `v0.5.4`. The `.github/workflows/release.yml` workflow automatically builds and attaches a clean source ZIP. No manual ZIP replacement is needed for users working from a Git checkout.

The local database, offline files, provider/OA caches, and `.env` remain outside source control.

Do not commit API keys, the SQLite database, or your offline corpus.

## Development and CI

Run:

```bash
python -m pytest -q
```

GitHub Actions contains a core test job and an optional Textual UI job. The tests are configured through `pyproject.toml` so imports do not depend on the directory from which pytest was started.

## Architecture

```text
                    source registry
              ┌─────────┼─────────┐
              ↓         ↓         ↓
          OpenAlex   Semantic    arXiv
                       Scholar
              └─────────┼─────────┘
                        ↓
                 retry + cache
                        ↓
                normalized Papers
                        ↓
             keyword + semantic rank
                        ↓
                    SQLite
                        ↓
          ┌─────────────┼──────────────┐
          ↓             ↓              ↓
        CLI            TUI           offline
          └─────────────┼──────────────┘
                        ↓
              explicit user feedback
                        ↓
               personal ranking
                        ↓
                optional LLM triage
```

## Roadmap

### v0.6 — citation intelligence

- query/store source references and cited-by links, not just their counts;
- related papers and prior/derivative work exploration;
- citation-aware discovery using a bounded citation graph;
- better cross-source identifier linking and citation graph tests.

### v0.7 — research digest

- scheduled new-paper scans;
- weekly/daily digest;
- possible-overlap warnings;
- reading-queue summaries.

### v0.8+ — research map/workspace

- citation/semantic graph;
- richer annotations;
- literature clusters;
- eventually a browser-based workspace after the TUI workflow is proven.

### Longer-term

- persistent vector indexing for large libraries;
- richer source adapters and provider-specific pagination/bulk endpoints;
- evidence-grounded LLM assessment with inspectable evidence;
- import/export interoperability with reference managers;
- browser-based UI only after the TUI workflow is stable.

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for the release history.
