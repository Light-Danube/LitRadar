# Browser research workspace implementation contracts

Base main dcd9363c (PR17 merged), no open PRs at start. Branch codex/web-research-workspace. User reports live CLI API succeeds locally (2026-10-14); cloud API restrictions are a separate historical limitation. New sixth research destination preserves previous five sections and Alt+1–5; optional Alt+6 for new page.

## Ownership
- Backend agent: web/research_api.py, web/research_files.py, tests/test_research_api.py, tests/test_research_files.py. Reuse venue_discovery and EvidenceStore. Root mounts router in workspace_web.py.
- UI agent: web/static/research-workspace.js, app.js, locales.js, styles.css, web/index.html, tests/web/research.cjs and test script registration. Existing nav IDs/shortcuts retain order. Sixth page research, local inline SVG/icon choices, EN/UK, preserved drafts, no LLM.
- Preset agent: storage/venue_presets.py, tests/test_venue_presets.py, docs/research/quick-venues.md. Independently research conservative quick-topic design; never fabricate source IDs/indexation. Default venue leads require explicit lookup/concrete identity selection.
- Orchestrator: workspace_web.py mount, CLI reuse optional data output, packaging, docs/AGENTS/.gitignore, integration tests/review and publication.

## Frozen HTTP contracts
All routes localhost only; synchronous handlers execute in worker threads and open own PaperStore; source config loaded only for explicit online actions. Network inputs capped, safe errors omit authenticated URLs.
- POST /api/research/venues/lookup {query,limit=10} -> {status,venues,next_step} using existing lookup.
- POST /api/research/search {source_id,query,year_from?,year_to?,limit=20,page=1,refresh=false,identifier?} -> original search_and_store result plus artifact {identifier,relative_path,files}. Every successful page, including empty/cache pages, is saved under data/research/<identifier>/ (default DB parent/research). Invalid identifier/collision rejected before network/ingestion. Search artifact persistence failure reported distinctly, cannot imply successful save.
- GET /api/papers/{paper_id}/evidence -> EvidenceStore.get.
- PATCH same {fields,expected_revision} -> updated worksheet; conflict409, invalid422/missing404. Also save worksheet snapshot under generated data bundle; returned artifact additive. Does not overwrite notes.
- GET /api/research/presets -> {items}; POST body fields -> item; PUT /api/research/presets/{id} {fields,expected_revision} -> item; DELETE same with expected_revision query -> {ok:true}. No background retrieval.
- POST /api/research/exports {paper_ids:[1..100],identifier?,research_question='',hypothesis='',disconfirming_evidence=''} -> artifact with saved manifest.json, matrix.md, matrix.csv. Does not auto-open/read user files.
- GET /api/research/artifacts?limit=20 -> {items} metadata only; GET /api/research/artifacts/{identifier}/{filename} -> bounded allowlisted FileResponse download. Never arbitrary paths or URLs.

## Preset interface
VenuePresetStore(store).list()->list[dict], .create(fields)->dict, .update(id,fields,expected_revision)->dict, .delete(id,expected_revision)->None. Object {id,revision,title,icon,query,venue_query,source_id:null|string,year_from:null|int,year_to:null|int}; fields partial on update. Icon whitelist beacon/book/chat/spark/globe/layers; bounded strings/count(20). Conservative default 3 topic leads, editable; seed once lazily and do not resurrect removed entries. Canonical source identity remains separate from venue display lookup query.

## UI behavior
Research page contains quick-topic cards/editable template form, explicit venue lookup and selected identity, bounded paper search/year controls, result IDs with metadata and scope warnings, library selection filter new/to-read/all (default to-read, show empty-state switch), user-authored evidence editor grouped fields with per-field provenance and global granularity/revision guard, selection-based Markdown/CSV export and recent saved bundles. Evidence values are blank until researcher enters them; never infer methodological findings. Drafts survive language/theme/page transitions, stale save conflicts preserve editor input. Form controls usable at narrow widths; markup escaped; keyboard labels and status announcements. No automatic scholarly/LLM requests on page load or quick-card selection.

## Persistence/tests
Generated identifiers UUID or safe user slug (ASCII letters/digits/hyphen/underscore, max64); exclusive bundle directories never overwrite, prevent traversal/symlinks. User-facing files under data/research, ignored by Git; tests use explicit temp DB/output roots. SQLite remains authoritative; file snapshots are portable timestamped results, not a replacement database. Synthetic API, filesystem containment/collision, preset revision/deletion, EN/UK DOM workflow/draft/error and full regressions; no production data/live provider tests.
