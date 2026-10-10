# LitRadar v0.7.1

Personal literature radar and research inbox for discovering, ranking, triaging, and keeping academic papers locally.

## Current release

**v0.7.1 — interactive Telegram bot, adjustable digest settings, and simpler Windows launchers.**

This release builds on v0.7.0 Research Digest and adds a private interactive Telegram command interface, buttons, configurable schedules, custom search topics, library queries, and simpler Windows dependency/CLI launchers. The SQLite schema remains additive; no database reset is required.

### What is new

- **Search workflow:** visible per-source progress in CLI/TUI, online source search from inside TUI, and a summary of fetched/new/library totals.
- **Personalization:** optional feedback-based ranking, explicit Useful/Not relevant feedback, and explanations of which research-profile groups influenced the recommendation.
- **Configuration:** `.env`, registered providers, API keys, timeouts/retries/backoff, and cached source-query results.
- **Offline access:** verified PDF downloads, readable PDF filenames, and optional legal open-access fallback through Unpaywall (`UNPAYWALL_EMAIL`).
- **Notes and exports:** structured note template through `$EDITOR`/`VISUAL`, Markdown literature-notes export, and BibTeX export with normalized, collision-safe citekeys.
- **Search:** SQLite FTS5 indexes title, abstract, venue, and personal notes when supported; a `LIKE` fallback remains available.
- **Citation intelligence:** persists references, cited-by edges, and related-work links; explores a bounded citation neighborhood from the CLI or TUI; reconciles DOI, arXiv, OpenAlex, Semantic Scholar, PMID/PMCID, and corpus identifiers where available. The original reference/citation counts remain available as metadata.
- **Telegram bot:** `telegram-run` / `run_telegram_bot.bat` listens for `/digest`, `/scan`, `/schedule`, `/settings`, `/topic`, `/search`, `/recent`, `/queue`, `/limit`, `/overlap`, and `/stats`; the bot also registers a command menu and inline action buttons. Schedule, digest-size, reading-queue, overlap, and search-topic settings persist in `digest_config.json` with bounded values. Only `LITRADAR_TELEGRAM_CHAT_ID` is allowed to issue commands.
- **Windows convenience:** `run_cli.bat` opens a persistent activated CLI shell; `setup_litradar.bat` is shared by launchers and installs core, UI, dev, and LLM requirement sets. The TUI launcher, updater, and schedule installer use the same dependency setup.

The LLM assessment remains experimental/advisory; it does not override the primary ranking or establish scientific novelty.

## Start here

For the quickest first launch on Windows, run `run_litradar.bat`. It creates `.venv`, installs `requirements.txt`, `requirements-ui.txt`, `requirements-dev.txt`, and `requirements-llm.txt`, initializes the database, and opens the TUI. Use `run_cli.bat` for a persistent CLI shell, or `run_telegram_bot.bat` to handle interactive Telegram commands. Scheduled digest delivery works independently of the Telegram listener. Use `run_litradar.ps1` in PowerShell or `./run_litradar.sh` on Linux/macOS.

To run a single CLI command through the launcher, pass arguments, for example `run_litradar.bat list --status to-read`.

```bash
python cli.py --help
python cli.py config
python cli.py init
python cli.py stats
python cli.py list --limit 50
python cli.py search "adaptive context emotion sarcasm"
python cli.py explore 42 --direction all --depth 1 --max-nodes 50
python cli.py ui
```

Every command has its own help page:

```bash
python cli.py search --help
python cli.py list --help
python cli.py download --help
python cli.py export-notes --help
python cli.py explore --help
```

Run the fixture without network access:

```bash
python cli.py ingest-fixture data/fixture.json --no-semantic
python cli.py list
python -m pytest -q
```

After publishing the repository, update a Git checkout through GitHub Desktop (`Fetch origin` → `Pull origin`) or run `update_litradar.bat` on Windows / `./update_litradar.sh` on Linux/macOS. The updater refuses to pull over tracked local edits, updates dependencies, runs `init`, and executes tests. It does not replace the local database, `.env`, or offline PDFs. If you installed LitRadar by extracting/copying a ZIP, `update_litradar.bat` can refresh all dependency sets but cannot fetch source code without `.git`; apply a newer patch/full ZIP manually or clone the repository with GitHub Desktop.
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
C       explore references, papers citing the selection, and related works
Ctrl+Enter / Fetch papers   search enabled online providers inside the TUI
?       keyboard help
Q       quit
```

The online source search is separate from the local library filter and displays source progress plus fetched/new/library totals. Search terms are highlighted in the selected paper's abstract when they match the local library filter. The detail view includes citation, reference, and (when available) influential-citation counts. Press `C` on a selected paper to explore its citation neighborhood in the background; results are added to the local library and the persistent activity panel shows provider/cache progress, final counts, and any provider errors.

The TUI also supports a `Personalized` sort. The displayed Score column changes to the current ranking score while the detail panel shows both the base and displayed scores.

Offline network work runs through a Textual worker so a slow PDF request does not block the main UI event loop.

## Citation intelligence (v0.6)

Citation exploration works on a bounded graph rather than downloading an unbounded network. A paper’s reference edges are stored as `citing paper → cited paper`; papers that cite the selected paper are stored in the opposite edge direction; OpenAlex `related_works` are stored as a separate undirected relation. Provider and fetch timestamps are retained so the local graph can be reused without calling every API again. The default citation cache TTL is seven days (`LITRADAR_CITATION_CACHE_TTL=604800`); `--refresh` bypasses that cache. The cache records the requested result limit, so increasing `--limit` triggers a wider lookup instead of silently reusing a narrower cached slice.

```bash
# Use a paper ID printed by `python cli.py list` or `show`
python cli.py explore 42 --direction both --depth 1
python cli.py explore 42 --direction all --depth 1 --limit 20 --max-nodes 50
python cli.py explore 42 --direction references --depth 2 --refresh
```

`--direction` accepts `references`, `cited-by`, `related`, `both`, or `all`. `depth` is limited to 1–2, the per-provider/per-direction result limit to 1–100, and unique traversal nodes to 1–200. These limits deliberately guard API usage and keep interactive exploration responsive. OpenAlex supplies reference lists, works citing a seed, and curated related works; Semantic Scholar independently supplies references and citing works. A provider can return no results because a record is missing from its index, identifiers could not be resolved, a rate limit was reached, or the API was temporarily unavailable—an empty result is not proof that the paper has no citations.

Schema migration is additive. `paper_identifiers`, `paper_relations`, and `citation_fetches` are created/backfilled without resetting the library. Matching prioritizes normalized DOI, arXiv ID without a version suffix, and provider identifiers; title matching remains a conservative fallback and does not merge identical titles that carry different explicit DOIs. No NetworkX or other graph package is required for the bounded traversal; SQLite handles durable edges and neighbor queries directly.

API documentation: [OpenAlex citation recipes](https://developers.openalex.org/guides/recipes) · [Semantic Scholar Academic Graph API](https://api.semanticscholar.org/api-docs/graph). [OpenCitations](https://opencitations.net/index/api/v2) is a possible future adapter, but not required for this release because the existing OpenAlex and Semantic Scholar integrations cover the current workflow.

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

To publish a release: update `VERSION`, `pyproject.toml`, and `CHANGELOG.md`; commit and push in GitHub Desktop; then create a GitHub Release using a matching tag such as `v0.6.0`. The `.github/workflows/release.yml` workflow automatically builds and attaches a clean source ZIP. No manual ZIP replacement is needed for users working from a Git checkout.

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

### v0.6 — citation intelligence — implemented in this release

- query and store references, cited-by edges, and curated related-work links;
- discover prior and derivative work using bounded breadth-first traversal;
- cache graph fetches and preserve provider provenance in SQLite;
- cross-source DOI/arXiv/OpenAlex/Semantic Scholar/PMID/PMCID/corpus ID linking;
- CLI `explore` command, TUI `C` action, and offline citation-graph regression tests.

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


## v0.7: scheduled research digest

### Edit your scheduled topics

Edit `digest_config.json`. It contains three example queries tailored to the current research profile. Each query can specify `name`, `query`, `sources`, and `per_source`. Keep limits modest at first; the example requests at most 20 results per source/query. `scan.semantic` defaults to `false`, which keeps background jobs lightweight and avoids first-run model downloads. Set it to `true` only if semantic dependencies/model availability are acceptable for scheduled runs.

### Run a scan or preview a digest manually

```bash
python cli.py scan
python cli.py digest --period daily
python cli.py digest --period weekly --output reports/weekly.md
```

`scan` runs all configured queries and upserts unique papers into the existing SQLite database. It writes a run summary to `research_runs`. A digest preview does not mark papers as delivered. A successful Telegram delivery is recorded separately; future Telegram digests start from the last successful delivery to avoid repeatedly sending the same newly stored papers. `--since 2026-10-01` overrides the period window.

The overlap section has two sources: high-overlap flags already stored by an optional LLM triage run, and local TF-IDF-style lexical similarity against the existing library. Thresholds and maximum candidate count are in `digest_config.json`. These warnings are pointers for human review, not a finding that a topic lacks novelty.

### Windows Task Scheduler

Run `run_litradar.bat` once to create `.venv` and install all four requirement sets, then use `install_schedule.bat` for the default daily scan + weekly digest, or install jobs individually:

```powershell
python cli.py schedule install --job scan --frequency daily --time 07:30
python cli.py schedule install --job digest --frequency weekly --time 09:00
python cli.py schedule status --job all
python cli.py schedule remove --job all
```

Times are local to Windows. Weekly jobs run on Sunday. Scheduled tasks use the current user's interactive session, start when an expected run was missed, and write logs under `logs/`. The computer must be powered on and the user logged in for the task to execute; if it was off/asleep, a missed task can run once it is available again. A local scheduler is preferable to keeping a Python scheduler process permanently open. For an always-on/server setup, use cron/launchd/systemd or a server/VPS; running the digest on GitHub Actions requires a separate decision about how to persist/sync the SQLite library.

### Optional Telegram delivery

1. Create a bot with Telegram's `@BotFather` and copy its token into `.env` as `LITRADAR_TELEGRAM_BOT_TOKEN`.
2. Open the bot and press **Start** or send `/start`.
3. Run `python cli.py telegram-chats`; choose the displayed chat ID and put it in `.env` as `LITRADAR_TELEGRAM_CHAT_ID`. Message contents from updates are not printed by this command.
4. Preview first; then send with `python cli.py digest --period weekly --send`. Never commit `.env` or share the bot token.

If Telegram is not configured, scheduled digest jobs save a Markdown report locally rather than failing or silently claiming delivery. No ChatGPT plugin/connector is required; LitRadar calls the Telegram Bot API directly.

#### Interactive Telegram command bot (v0.7.1)

The scheduled Task Scheduler job sends digests without a permanently running bot process. To use slash commands and inline menu buttons, configure both `LITRADAR_TELEGRAM_BOT_TOKEN` and `LITRADAR_TELEGRAM_CHAT_ID`, then run `run_telegram_bot.bat` and keep that window open. The polling process receives commands only from the configured chat ID and saves its update offset under `data/telegram_bot_state.json`. Do not run multiple `telegram-run` instances or use `telegram-chats` concurrently with the listener; Telegram allows only one active `getUpdates` poller per bot token.

Useful commands:

```text
/start /help
/digest daily                 # generate and send a digest now
/digest weekly
/schedule daily 08:00         # change scheduled delivery time
/schedule weekly 09:00        # weekly jobs run on Sunday
/limit 10                    # 1–30 new papers per digest
/queue 5                     # 0–10 queue items included in digest
/overlap off                 # suppress overlap section
/topics                      # inspect active research queries
/topic add irony | context-aware irony detection
/topic remove irony
/search context attribution  # search the local library
/recent /stats
```

`/schedule` updates the digest's Windows Task Scheduler job as well as the configuration. On Linux/macOS it records the setting and reminds you that cron/launchd must be updated separately. Search-topic commands are intentionally bounded: at most 10 configured topics, a maximum of 200 query characters, and a conservative default of 10 results per provider per topic.

### Cross-platform schedule entry point

The native installer in `python cli.py schedule ...` currently configures Windows Task Scheduler. On Linux/macOS, use the OS scheduler to invoke:

```cron
30 7 * * * /absolute/path/to/.venv/bin/python /absolute/path/to/LitRadar/cli.py scheduled-run --job scan
0 9 * * 0 /absolute/path/to/.venv/bin/python /absolute/path/to/LitRadar/cli.py scheduled-run --job digest --period weekly
```

Keep the project `.env` readable by the user running the scheduled job.
