# LitRadar v0.5.0

Personal literature radar and research inbox for discovering, ranking, triaging, and keeping academic papers locally.

## Current release

**v0.5.0 — personalization + source configuration + resilient source fetching.**

This release keeps the v0.4.x SQLite database compatible. No database reset is required.

### What is new

- Runtime configuration via `.env` / environment variables.
- Registered source providers with configurable enable/disable list.
- Concurrent source fetching with per-source timeout, retry, exponential backoff, and local query-result cache.
- `python cli.py config` for a masked view of effective configuration.
- Lightweight personalized ranking based on explicit feedback plus conservative workflow signals.
- Explicit positive/negative feedback via CLI and TUI (`Y` / `N`).
- `personalized` library/top sorting.
- Feedback is intentionally inactive until a configurable minimum number of useful interactions is available.
- OpenAlex API-key configuration aligned with its post-February-2026 API authentication model.

## Start here

```bash
python cli.py --help
python cli.py config
python cli.py init
python cli.py stats
python cli.py list --limit 50
python cli.py ui
```

Every command has its own help page:

```bash
python cli.py search --help
python cli.py list --help
python cli.py feedback --help
python cli.py ui --help
```

Run the fixture without network access:

```bash
python cli.py ingest-fixture data/fixture.json --no-semantic
python cli.py list
pytest -q
```

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
python cli.py list --sort personalized
```

`list` intentionally keeps a default display limit of 50, while reporting the full matching count. Use `--limit` when you want more rows.

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
```

Offline bundles live under `data/offline/` and can include metadata, abstract, notes, BibTeX, and an available PDF.

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
?       keyboard help
Q       quit
```

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
 data/source_cache/  # cached provider results
.env                 # secrets and local configuration
```

These are intentionally excluded from Git.

Additive SQLite migrations are applied automatically. Upgrading from v0.4.x does not require a database reset.

## Upgrading with GitHub Desktop

Once the repository is published:

1. Use **Fetch origin → Pull origin** to receive a release.
2. Reinstall/update Python dependencies if `requirements*.txt` changed.
3. Run:

```bash
python cli.py init
pytest -q
```

The local database, offline files, cache, and `.env` remain outside source control.

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

- references / cited-by;
- related papers;
- prior and derivative work exploration;
- citation-aware discovery;
- better cross-source identifier linking.

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

- stronger persistent vector indexing for large libraries;
- SQLite FTS5 for full-text search at scale;
- richer source adapters and provider-specific pagination/bulk endpoints;
- evidence-grounded LLM assessment;
- import/export interoperability with reference managers.

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for the release history.
