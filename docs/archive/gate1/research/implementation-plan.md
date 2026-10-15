# Venue discovery first delivery (unreleased)

Base: main `08f8ca660a093c84546c3ec4690ef85755180a68`, verified identical through GitHub compare on 2026-10-14. No open PRs reported. Git fetch currently fails because proxy:8080 is unreachable.

## Reuse and ownership
- Orchestrator: CLI integration (`cli.py`), venue persistence (`storage/sqlite.py`), service (`venue_discovery.py`), packaging, README/ROADMAP/CHANGELOG/CODEX-HANDOFF and combined verification.
- Venue agent: `sources/venues.py`, `tests/test_venue_sources.py`. Reuse OpenAlex `_get_json`, `_work_to_paper`, shared bounded HTTP retries; leave broad registry/search unchanged.
- Evidence agent: `storage/evidence.py`, `evidence_matrix.py`, `tests/test_evidence_matrix.py`. Separate additive worksheet tables on the existing PaperStore connection; never update papers.notes. No LLM calls.
- Review agent: `docs/archive/gate1/research/erc-context-novelty-matrix-2026.md` and research source ledger only. Bibliographic facts must be verified; blocked sources and candidates remain explicit.

## Interfaces and contracts
Venue adapter: lookup_venues(query, *, limit=10, timeout=20, retries=2, backoff=1, api_key=None) -> list[Venue]; get_venue(source_id, same HTTP kwargs) -> Venue; search_venue(query, source_id, *, year_from=None, year_to=None, limit=20, page=1, same HTTP kwargs) -> VenueSearchResult. Venue/result expose to_dict() or dataclasses.asdict. Concrete source IDs only (S + digits); structured primary_location.source.id filter, bounded pages/results, no name-based match or generic-search post-filter. Provider exceptions propagate distinctly. Venue provenance never certifies review or Scopus/WoS.

Persistence: additive venue records and paper-venue observations keyed by concrete provider source ID, separate from paper metadata; UTC observation time/query/record URL/status retained. Search cache includes provider, source identity, query, years, limit/page and TTL. Canonical ingestion reuses existing dedup; retain scores and user state on refresh. Reject conflicting explicit DOI aliases rather than merging.

Evidence: independent bounded, human-editable per-paper worksheet with revision conflict guards and provenance, exported deterministically to escaped UTF-8 Markdown/CSV. Interface EvidenceStore(store), get(paper_id), update(paper_id, fields, expected_revision=0); export_markdown(store, paper_ids, *, research_question='', hypothesis='', disconfirming_evidence='') -> str; export_csv(store, paper_ids) -> str. Missing evidence explicitly not verified, metadata-only default, no notes/profile upload.

## Stages and checks
1. CLI `venue lookup`, `venue search` by selected ID with inclusive year bounds and explicit online action. Browser handoff: existing inbox views ingested IDs; narrow browser discovery deferred.
2. CLI editable evidence JSON worksheet and Markdown/CSV export, separate from personal notes.
3. Review artifact: aim for 12–20 verified papers including counterexamples, otherwise report accessible coverage and unverified candidates.
4. Synthetic/disposable DB tests for identities, structured filtering/cache/error statuses, migration, dedup and user-state preservation, evidence conflicts/export escaping. Run full Python and Node suites, diff check; no live LLM or production data. Live scholarly API and rendered-browser checks reported separately.
5. Commit dedicated branch, push or equivalent connector Git objects, immediately create Draft PR; never merge. Keep v0.8.0 unchanged.
