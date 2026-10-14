# Venue discovery and evidence worksheet (unreleased)

[Russian step-by-step CLI workflow and practical significance](cli-workflow-ru.md).

The CLI was the first end-to-end interface; [Research browser workflow](web-workspace.md) now offers the same retrieval and editable evidence. Existing `search` remains broad discovery; `venue` performs an explicit OpenAlex Sources/Works request. No automatic search, Crossref enrichment or model inference is added. Scholarly metadata is untrusted provider evidence, not certification.

## Choose an identity, then search

```sh
python cli.py --db scratch.sqlite venue lookup "Computational Linguistics" --limit 10
# Inspect source_id, name, ISSN-L/ISSNs, type, publisher/host and record URL.
# Replace SOURCE_ID with the exact S+digits identity returned above.
python cli.py --db scratch.sqlite venue search SOURCE_ID "emotion context" --year-from 2023 --year-to 2026 --limit 20
python cli.py --db scratch.sqlite venue search SOURCE_ID "emotion context" --year-from 2023 --year-to 2026 --limit 20 --page 2
python cli.py --db scratch.sqlite list --status all
python cli.py --db scratch.sqlite web
```

`SOURCE_ID` is a placeholder, not a claimed journal identifier. Same-name results are `ambiguous_venue`; select a concrete ID. Journals and proceedings are different categories. arXiv is a preprint repository. Hosting platforms do not identify a journal. Missing types are `unknown`. Lookup stores metadata, not inferred aliases or indexing claims. Scopus/WoS and peer-review status remain `unverified`.

Search applies `primary_location.source.id:S…` and inclusive `publication_year:2023-2026` at retrieval time, never a top-20 broad-search post-filter. Returned identities/years are checked; contradictory or malformed data fail the whole page. **Only primary publication sources are queried**; alternative locations and conference editions with different source IDs can be missed. This is not a venue-complete bibliography. `count` and `truncated` report provider page coverage, not global completeness. Conferences need concrete source records; acronym text does not substitute for identity. No ISSN is required.

CLI bounds: 1–100 results, pages 1–10, queries 1–500 characters and years 1000–9999. HTTP timeout/retries/backoff are capped at 60 seconds/3 retries/5 seconds, and each retry wait at 60 seconds. Existing `LITRADAR_SOURCE_*` configuration and optional `OPENALEX_API_KEY` apply. Cached successful pages, including empty results, use keys with provider/source/query/years/limit/page; TTL is `LITRADAR_SOURCE_CACHE_TTL`. `--refresh` bypasses cache. The most recent 100 page entries are retained. Cached metadata keeps its original observation timestamp. Errors are not cached. No secrets enter stored provenance or displayed error URLs.

Search results are now saved to local `data/research/<identifier>/` bundles; see the [storage contract](web-workspace.md#where-results-are-stored). Without `--output`, `evidence export` saves both Markdown and CSV there.

JSON distinguishes `zero_results`, `ambiguous_venue`, `rate_limited`, `timeout`, `metadata_inaccessible`, `network_unavailable`, `provider_error`, `malformed_metadata` and `invalid_request`; venue verification/type/status are separate fields. Every search emits a start event. The existing inbox opens returned canonical `paper_ids`. The new [Research browser section](web-workspace.md) adds localized lookup, evidence editing and saved result bundles while retaining the original five sections.

## Editable evidence, independent of notes

```sh
python cli.py --db scratch.sqlite evidence show 1
python cli.py --db scratch.sqlite evidence update 1 fields.json --expected-revision 0
python cli.py --db scratch.sqlite evidence export 1 2 --output matrix.md --research-question "Does selected context help?" --hypothesis "A small task-aware subset may preserve accuracy"
python cli.py --db scratch.sqlite evidence export 1 2 --format csv --output matrix.csv
```

IDs above are illustrative; use your own returned IDs. `fields.json` is a partial fields mapping, for example:

```json
{
  "user_questions": {"value": "Does thread context outperform a fixed window?", "origin": "user"},
  "context_selection": {"value": "not in abstract", "origin": "abstract_review", "source_ref": "https://doi.org/REPLACE_WITH_REAL_DOI", "location": "Abstract", "reviewed_at": "2026-10-14"}
}
```

The URL is an explicit placeholder; replace with a real reviewed source. `evidence show` lists supported fields and the current revision. Read its `fields` object to make round-trip edits; `update` accepts that object, not the entire show envelope. Unspecified fields remain intact. Provenance supports source reference/type, review location/time, verification status and server recording time. Imported/abstract/full-text reviewed statements require a source reference; verified statements also require one. Origins describe user declarations, not independently audited truth. An abstract review never implies full-text review. No model-generated fields are supported by this first delivery.

Inputs are capped at 200 KB; individual strings at 8000 characters; a worksheet at 100000 UTF-8 bytes. Exports select 1–100 canonical IDs in the CLI, sorted deterministically, escape Markdown/HTML and CSV formula prefixes, and exclude personal notes. Fields may state author limitations, user hypotheses, alternative explanations, strongest counterexample, known prior art, differences, falsification and verification needed. Default findings are `not verified`, quality `metadata only`; candidate gaps always remain unverified. No certified dissertation novelty categories are assigned.

## Additive storage and recovery

`PaperStore` adds `discovery_venues`, `paper_venue_observations` and `venue_search_cache`. The optional `EvidenceStore` lazily adds `evidence_worksheets` and `evidence_worksheet_revisions` to the same connection/database. No existing columns are removed or renamed. Venue observations preserve original provider venue text and complete lookup metadata independently of `papers.raw_json`, which providers may refresh.

Search ingestion and cache writes are one transaction. Existing deduplication merges same DOI records; conflicting explicit DOIs on a provider alias abort instead of overwriting metadata. Existing relevance/semantic scores and personal state are retained; new venue results have unranked zero scores until an existing ranking workflow runs. Citation relations are untouched. Worksheet updates require the current revision and retain prior revisions. There is no delete/restore UI yet: recover a prior worksheet by reviewing a revision in the supplemental table and reapplying its fields with the latest revision guard, creating another revision. Before upgrading a real library, use your normal closed-application backup; this task exercised disposable synthetic databases only.

Rollback application code does not require dropping supplemental tables. Old versions ignore them. Do not reset the library or overwrite primary notes to roll back this feature.

## Verification limits

Synthetic API tests cover collisions, conference/preprint/platform/unknown types, no ISSN, malformed records, request bounds, 429/5xx/retry/timeout and filtered contamination. Integration checks cover cache separation, atomic rollback, additive migration, paper state preservation, local edits and export. Full local results are recorded in the delivery validation note. No production databases, credentials, private PDFs or live LLM services were used.

On 2026-10-14, two unauthenticated, bounded live probes of OpenAlex Sources and Crossref Works failed through the session proxy: `Tunnel connection failed: 403 Forbidden`. The configured allowlist omits these API domains; no bypass was attempted. Live OpenAlex authentication, schema/coverage and provider costs remain unverified. Crossref is not implemented. Literature verification used separate accessible connector sources, documented in the review ledger; it is not a live adapter smoke pass.
