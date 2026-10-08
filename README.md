# LitRadar v0.4.5

A small personal literature radar and research inbox. LitRadar finds papers from multiple academic sources, ranks them against a research profile, stores them locally in SQLite, and lets you triage, tag, save offline, and export citations.

## Current release

**v0.4.5 — TUI/library bridge + source metadata + deduplication.**

This patch stays compatible with the existing v0.4.x database. No database reset is required.

### What is new

- TUI paper details now show citation count and source-derived tags.
- TUI shows the number of papers matching the current view and provides a tag filter.
- Tag filtering works against both manual tags and tags extracted from source metadata.
- Search results can merge records found through multiple providers using normalized title hashes, DOI, and arXiv identifiers.
- Cross-source links are retained instead of being discarded when a duplicate is refreshed.
- `python cli.py list` now explicitly reports `Showing X of Y`.

## Recent release history

- **0.4.5** — TUI count/tag improvements, citation count in details, source-derived tags, conservative cross-source deduplication, and source-link preservation.
- **0.4.4** — fixed Textual test lifecycle by using `App.run_test()` and added `pytest-asyncio`.
- **0.4.3** — TUI help, sorting, tag editor, offline hotkey, and related UX hardening.
- **0.4.2** — CI import-path fix plus SQLite/embedding ingestion improvements.
- **0.4.1** — offline bundles and BibTeX export.
- **0.4.0** — research inbox workflow, filtering, status tracking, notes/tags, and TUI foundation.

For detailed file-level changes and bug fixes, see [`CHANGELOG.md`](CHANGELOG.md).

## Start here

```bash
python cli.py --help
python cli.py init
python cli.py stats
python cli.py list --limit 50
```

Every command has its own help page:

```bash
python cli.py list --help
python cli.py search --help
python cli.py review --help
python cli.py ui --help
```

Run the fixture without network access to verify the installation:

```bash
python cli.py ingest-fixture data/fixture.json --no-semantic
python cli.py list
pytest -q
```

## Core workflow

### Find and rank

```bash
python cli.py search "adaptive context emotion sarcasm"
python cli.py search "context selection" --sources openalex semantic_scholar arxiv --per-source 20
```

The default ranking combines keyword and semantic relevance. Semantic embeddings are optional at runtime; LitRadar falls back to keyword scoring if the embedding backend is unavailable.

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
```

`list` keeps the default output limit at 50 so an accidentally large library does not flood the terminal, but it now reports the full matching count. Use `--limit` explicitly when you want more rows.

### Read / dismiss / tag

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

Manual tags are preserved across provider refreshes. Source-derived tags are stored separately so a metadata refresh cannot erase your own organization. Both kinds are visible to library filtering.

### Offline reading and bibliography

```bash
python cli.py download 42
python cli.py download --status to-read --limit 10
python cli.py open 42
python cli.py export-bibtex 42 --output paper.bib
python cli.py export-bibtex --status read --output read.bib
```

Offline bundles live under `data/offline/` and include metadata, abstract, notes, BibTeX, and a PDF when an accessible open PDF exists.

## Textual TUI

Install the optional UI dependency:

```bash
python -m pip install -r requirements-ui.txt
python cli.py ui
```

The TUI is designed as a fast research inbox rather than a full reference manager. It provides:

- status filtering;
- text search;
- sorting by relevance, publication date, date added, title, and citations;
- tag filtering;
- paper details including citation count and source tags;
- total-library and current-view counts;
- tag editing;
- offline saving in a background worker;
- local-first opening of saved PDFs.

Useful keys:

```text
↑ / ↓   select paper
Enter   select row
T       To Read
R       Read
D       Dismiss
U       Restore
G       Edit tags
K       Tag filter
L       Save offline
O       Open local PDF / URL
/       Search
F       Status filter
S       Sort
?       Help
Q       Quit
```

## Automatic source tags

When available, LitRadar extracts lightweight subject/category metadata:

- OpenAlex keywords;
- Semantic Scholar fields of study;
- arXiv category identifiers.

These values are stored in `source_tags_json` and participate in tag filtering without overwriting manually curated tags.

## Deduplication

LitRadar uses several conservative identifiers when importing papers:

1. DOI, normalized to its identifier form;
2. arXiv identifier, when available;
3. SHA-256 of a normalized title (`lower/casefold + punctuation removed + whitespace normalized`).

When a match is found, LitRadar updates the existing record instead of inserting another paper. Cross-source metadata is retained in `source_refs_json`. Existing manual status, tags, notes, and timestamps remain intact.

The title hash intentionally stays conservative. It handles punctuation/case/title-format differences but does not attempt aggressive fuzzy matching of substantially different titles.

## Configuration

Edit `research_profile.json` to change the research profile, weighted keyword groups, semantic/keyword weights, and embedding model.

Environment variables currently used by optional providers include:

```text
LITRADAR_MAILTO
SEMANTIC_SCHOLAR_API_KEY
OPENAI_API_KEY
ANTHROPIC_API_KEY
OLLAMA_HOST
```

More source/provider configuration is planned for v0.5.

## LLM assessment

LLM assessment is still experimental/advisory. It does not decide scientific novelty and does not alter the primary ranking.

```bash
python cli.py assess --provider ollama --model llama3.1:8b --limit 5
```

For now, treat the assessment as an additional signal to inspect rather than as a final literature-review decision.

## Database and upgrades

The local database is:

```text
data/litradar.sqlite3
```

**Do not delete it when upgrading.** LitRadar applies additive schema migrations automatically. Your local offline directory is also preserved.

Recommended Git-based update workflow:

```bash
git pull
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip install -r requirements-ui.txt
python cli.py init
pytest -q
```

Install only the optional dependency groups you use.

## GitHub Desktop

Create the repository by adding the local LitRadar folder in GitHub Desktop, then **Publish repository**. The included `.gitignore` keeps `data/*.sqlite3`, `data/offline/`, `.env`, `.venv/`, caches, and IDE metadata out of Git.

After publication, use **Fetch origin → Pull origin** for future releases rather than replacing the project folder. The local database and offline files are intentionally outside version control.

Commit the code changes, not your local research database or secrets.

## Development

```bash
python -m pytest -q
```

CI runs the core suite and the optional Textual UI suite with the UI dependency installed.

## Architecture

```text
sources/       OpenAlex / Semantic Scholar / arXiv
    ↓
normalized Paper objects + source metadata
    ↓
keyword + semantic ranking
    ↓
SQLite library + deduplication
    ↓
CLI / Textual TUI / offline bundles / BibTeX
    ↓
optional LLM assessment
```

## Roadmap

### v0.5 — personalization and source configuration

Planned: `.env`/provider configuration cleanup, a source registry, more source enable/disable controls, and personalized ranking using `to-read`, `read`, `dismissed`, tags, and other explicit user feedback.

### v0.6 — citation intelligence

References, cited-by, related papers, prior/derivative work exploration, and citation-aware discovery.

### v0.7 — automated research digest

Scheduled digests with new highly relevant papers, possible overlap warnings, and reading-queue summaries.

### v0.8+ — research map / workspace

Graph-based literature exploration, richer annotations, and eventually a browser-based workspace after the workflow is proven in the TUI.

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for release-by-release changes and bug fixes.
