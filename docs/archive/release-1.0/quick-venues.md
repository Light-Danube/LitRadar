# Quick venue templates

Quick cards save a **research topic and venue lookup lead**. They reduce repeated typing without certifying a journal identity or running background searches. Selecting a card populates the research form; the researcher explicitly looks up a venue, selects a concrete returned OpenAlex source identity, and starts a bounded paper search. A saved source ID remains a remembered selection and is checked by the existing venue-search workflow.

## Default leads and fit

| Topic card | Initial keyword query | Venue lookup lead | Why investigate |
| --- | --- | --- | --- |
| ERC context | emotion recognition conversation context | Computational Linguistics | Journal focused on computational language/NLP; includes verified conversation-context sarcasm research in [the existing evidence review](../gate1/research/erc-context-novelty-matrix-2026.md#r05--sarcasm-analysis-using-conversation-context) |
| Sarcasm in discussion | sarcasm conversation context | Transactions of the Association for Computational Linguistics | NLP journal; a lead to investigate, with no promise of results for this particular query |
| Affective context | emotion recognition context selection | IEEE Transactions on Affective Computing | Affective-computing journal whose stated scope includes recognition/interpretation of human emotions |

Official pages checked through the Exa connector on 2026-10-14: [Computational Linguistics at MIT Press](https://direct.mit.edu/coli), [TACL journal site](https://transacl.org/index.php/tacl), and [IEEE Computer Society's TAC scope/call](https://www.computer.org/digital-library/journals/ta/tac-general-call-for-papers). These support journal title/scope only. They do not independently verify a current OpenAlex ID, Scopus/WoS indexing, keyword coverage, paper quality or novelty. The CSDL journal route's extracted topics were unrelated; its noisy extraction was not used to infer research fit.

The defaults deliberately store **source_id = null**, no year restriction, and editable query/name text. No invented OpenAlex IDs or ISSNs are seeded. Resolve the full title rather than assuming an acronym uniquely identifies a source. Conference templates may be added by the user with a verified source selection; journals and conference proceedings remain different publication categories. MIT Press and IEEE are publishers; ACL Anthology and IEEE Xplore are hosts/indexes; none should become an individual venue simply from its host name.

## Interaction and accessibility

Cards group topics, not papers or certified venues. Each card has a visible title and a local icon from beacon/book/chat/spark/globe/layers; icons supplement text and cannot carry the only accessible name. Editing title, query, lookup lead, optional saved source ID and year range is a separate action from lookup/search. Language or theme changes should preserve unsaved input. A stale revision returns a conflict so that the browser retains the draft and offers reload instead of silently overwriting another edit.

The template's venue lookup text is descriptive. Exact retrieval uses its separately selected source ID; changing the name is not proof that the saved ID identifies the new venue. The interface should clear/reselect an identity when intentionally changing the venue target, or clearly display the still-selected concrete identity before retrieval. Merely choosing a topic card or opening the page performs no scholarly API or LLM request.

## Storage contract and recovery

`VenuePresetStore(PaperStore)` exposes `list()`, `create(fields)`, `update(id, fields, expected_revision)` and `delete(id, expected_revision)`. Returned keys are exactly `id`, `revision`, `title`, `icon`, `query`, `venue_query`, `source_id`, `year_from`, `year_to`. IDs are positive integers; create starts revision 1. Updates merge partial supported fields. The three text fields must be nonempty, bounded to 120/500/200 characters respectively; unsupported icons/fields, NUL characters, malformed source identities, boolean years and reversed ranges are rejected. Source IDs normalize through the existing conservative OpenAlex validator, accepting an S-digit ID or its exact public OpenAlex URL. Optional years range from 1000 through 9999; this is an input bound, not a claim of available scholarly coverage.

Two additive tables store templates and a seed marker on the existing SQLite connection. At most 20 **active** templates are allowed, including defaults. Lazy initial seeding is atomic and happens once. Deletion retains a tombstone and increments the revision; a later list/reopen never resurrects it. Deleted IDs are not reused. Templates are independent of paper metadata, notes, tags and reading status. Existing enclosing SQLite transactions remain intact through savepoints.

A stale positive revision raises `ValueError` containing “changed” (HTTP 409); invalid input raises `ValueError` (HTTP 422); missing/deleted IDs raise `KeyError` (HTTP 404). Keep the complete database backup for recovery. Deletion retains the row but this delivery exposes no restore API; recovery requires an explicitly reviewed database operation or recreating the template as a new ID. Removing/recreating the seed marker is not a recovery mechanism and does not overwrite existing user state.

Tests use disposable databases and synthetic inputs, covering seed/deletion across reopen, concurrent revisions, active bounds, source validation, Unicode and preservation of unrelated paper state. Official-site connector checks do not prove live cloud OpenAlex API availability or native browser rendering.
