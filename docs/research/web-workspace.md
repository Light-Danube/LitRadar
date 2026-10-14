# Research browser workspace (unreleased)

Open `python cli.py web`, then select **Research** in the sidebar (or Alt+6). Existing Overview/Inbox/Graph/Clusters/Jobs destinations and Alt+1–5 remain in their original order. EN/UK and System/Light/Dark are shared with the rest of the workspace.

## Find a venue and build a reading comparison

1. Select a quick-topic card or enter a venue name and research terms. Selecting a card fills the form; it does not contact a scholarly provider. Default cards are editable leads for ERC context, sarcasm in discussion and affective context, with no fabricated source IDs.
2. Explicitly run venue lookup and choose a concrete OpenAlex source identity. Check title, source ID, type, ISSNs/ISSN-L and publisher/host metadata. A similarly named result may be a different venue; a publication host is not a journal. Review/index membership remains unverified.
3. Run a bounded keyword/year search, optionally naming its saved result bundle. The existing structured primary-source/year retrieval, contamination checks, cache keys and deduplication are reused. Result paper IDs belong to the same library. Empty pages, ambiguity and errors stay distinguishable. Every successful search page, including cached/empty pages, receives a portable saved snapshot.
4. Select papers from the reading list. Its default is **To read**; switch to **New** or **All** to reach freshly ingested results or older records. Filters do not change paper workflow status. Existing inbox links remain available.
5. Fill the evidence form for a selected paper. Fields cover task/data, context and selection, method/baselines/datasets/metrics/outcomes, author-stated limitations and your own hypotheses/counterexamples/validation plans. Provenance and reviewed granularity are explicit; no method, metric or gap is invented to fill a blank template. Save uses the current worksheet revision and creates an immutable file snapshot alongside the SQLite update.
6. Select canonical paper IDs and export a comparison. Markdown and CSV are saved locally with an accompanying manifest and can be downloaded from the saved-bundle list. Research question, hypothesis and disconfirming evidence remain editable context, not certified conclusions.

Search, evidence and preset drafts are preserved in page state through navigation and language changes; theme changes do not rebuild the editor. A stale revision conflict preserves user input for comparison/retry rather than silently overwriting another session. Default file naming is automatic; entering an existing name produces a conflict and keeps the previous bundle untouched.

## Quick venues

[Design and journal sources](quick-venues.md) explains why a card stores topic query + venue lookup query + optional chosen source ID, instead of guessing that a journal name identifies a unique indexed source. Users can add/edit/remove templates and select one of six local icon styles; no icon URLs or remote scripts are fetched. Presets are stored on the existing SQLite connection in supplemental tables, with guarded edits and deletion tombstones. Seed defaults are inserted once, so a removed default does not reappear after restart.

## Where results are stored

With the default `data/litradar.sqlite3` library:

```text
data/research/<generated-or-user-identifier>/
  manifest.json
  search.json       # a search result bundle
  evidence.json     # a saved worksheet snapshot bundle
  matrix.md         # an export bundle
  matrix.csv        # the same export bundle
```

These are separate bundle kinds; every directory contains its own manifest and the relevant content files. Identifiers are generated UUIDs or unique user names consisting of 1–64 ASCII letters/digits/hyphens/underscores. Cyrillic can be used in research text/template titles; filesystem identifiers use the bounded portable format. Windows device names (CON/PRN/AUX/NUL/COM1–9/LPT1–9, case-insensitive) are rejected before a provider call. Existing directories are never overwritten. Pending/failed writes are cleaned up; snapshot size and download filenames are bounded. No arbitrary server path/URL is accepted.

For an explicitly chosen custom database, the output root is its parent directory plus `research/`; tests can inject a disposable root using `create_app(..., research_results_root=...)`. The saved-bundle list reads bounded metadata (up to 1000 directory entries, returning up to 100 records), not evidence content. Corrupt manifests are ignored; saved files remain in the result folder even when outside that bounded listing. Result directories are ignored by Git and already excluded from Docker build contexts through `data/`. Downloads are attachments, not rendered untrusted documents.

SQLite is the authoritative editable store. Bundles are timestamped snapshots: later paper refreshes or evidence edits do not retroactively change an old export. Personal research notes are excluded from evidence exports. If filesystem persistence fails after a database save, the API reports `save_failed` with `saved_in_database: true`; reload the worksheet/results before retrying so the successful revision is not mistaken for rollback. Do not reset your library to fix a folder-permission error.

The CLI also saves venue-search snapshots in this result store. `venue search ... --identifier context-pilot` selects a unique name. `evidence export 42 43` without `--output` saves both Markdown and CSV to an automatic bundle; `--identifier context-comparison` names it. Existing explicit `--output matrix.md` / `--format csv --output matrix.csv` behavior remains available for caller-chosen files; do not combine `--output` and `--identifier`.

## API and preservation

Research routes are in `web/research_api.py`; shared CLI retrieval stays in `venue_discovery.py`; worksheet validation/revisions stay in `storage/evidence.py`. All provider requests require an explicit POST lookup/search action. Ordinary list, edit and export operations are local. Router body sizes, paper batches, pagination, fields and filenames are bounded. Server still binds only to localhost and adds no remote accounts/sync or implicit LLM calls.

Additive preset tables, existing evidence tables and immutable result directories require no destructive migration. Provider refresh retains canonical IDs, existing notes/tags/status/relations and scores. A deleted shortcut can be recreated as a new template; its tombstone prevents seed resurrection. Historical worksheet records remain available through existing revision storage; no new destructive evidence-delete action is added.

## Verification and limits

The user confirmed real CLI OpenAlex retrieval works on their installation on 2026-10-14. This is useful user-reported validation; no independent live browser search is claimed here. Historical cloud proxy 403 results remain recorded as environment-specific failures. This browser increment is checked with synthetic HTTP/database/filesystem fixtures and EN/UK DOM workflows; current counts and rendering limitations are recorded in the delivery handoff.

The review artifact is still a bounded literature review, largely abstract-based. A filled matrix helps compare evidence; it does not automatically establish academic novelty, peer review or Scopus/WoS membership. Full-text competitor review and controlled experiments remain the next research steps.

## Executed checks (2026-10-14)

- Python 3.12 full suite: **405 passed, 0 failed, 0 skipped**, one existing Starlette/httpx deprecation warning. Uses disposable SQLite databases, explicit temporary result roots and mocked scholarly HTTP. No production data or live LLM calls.
- Full Node suite: **6 test files passed, 0 failed, 0 skipped**. **10 new research DOM scenarios passed**. They exercise EN/UK lookup/source selection, status filters, paper selection, evidence/provenance editing, exports/download links, presets, escaping, draft retention, stale conflicts, slow requests and explicit database-save/file-failure messages. These execute production scripts with jsdom; rendering is not verified.
- Changed Python compilation, JS syntax, Markdown path checks and whitespace validation passed. Windows workflow now includes new research suites; no actual Windows Actions result claimed.
- Sandboxed Chromium was attempted and aborted before rendering because `/usr/lib/chromium/chrome-sandbox` is not configured with the required SUID ownership/mode. No `--no-sandbox` run or new screenshots were used. Desktop/narrow CSS and control labels were reviewed structurally and in DOM tests, not through a visual browser pass.
- Live CLI retrieval is user-reported successful. Independent live browser-provider verification and remote CI results remain separate gates.
