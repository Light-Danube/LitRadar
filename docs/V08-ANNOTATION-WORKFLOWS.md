# v0.8.x annotation adapters, recovery and graph layout

This increment builds on main `ef5ecd06` in branch `codex/annotation-adapters-graph`. The user accepted the existing WebUI visual/functionality on 2026-10-14 and requested that the additional cloud-browser acceptance gate be skipped. No new real-browser rendering claim is made for these controls.

## Import into the selected paper

Open **Additional annotations → Import and local extraction**. Select one or several JSON, RIS, BibTeX or PDF files. All parsed records attach to the selected paper as supplemental imported annotations; they do not create/merge library papers or overwrite research notes.

- At most 10 files, 5 MB decoded bytes combined, 100 entries and 1 MB parsed annotation payload. The request stream is capped at 7 MB before JSON/base64 parsing.
- JSON is a UTF-8 array of `{content, source_ref?}`; null source references remain supported. RIS uses complete `TY`/`ER` records, including notes/abstracts and bibliographic context. BibTeX handles parsed records and nested fields.
- PDF imports comments and extractable page-text excerpts, at most 50 pages and 10,000 text characters per page. The source labels distinguish comments from text excerpts. Image-only OCR and encrypted PDFs are not supported. Highlights without textual comments are represented through page text rather than a claim of exact highlighted text extraction.
- JSON/RIS need no extra dependency. Install PDF/BibTeX adapters with `python -m pip install -r requirements-annotations.txt` or package extra `litradar[annotations]`. Missing adapters return 503 rather than a misleading empty success.
- PDF/BibTeX run in a separate Python parser process with a 15-second wall timeout. POSIX workers cap address space at 512 MB and CPU at 12 seconds; Windows retains the timeout. This is resource bounding, not a general-purpose security sandbox.
- No uploaded file is persisted, no source path is opened, no URL is fetched and no PDF script is executed. Filenames/references are labels only. The server reads the uploaded bytes.
- Validate all files before committing. An invalid file aborts the complete batch. Repeating the same filename/content/adapter is repeat-safe. The existing JSON endpoint remains compatible and shares its identity with the new JSON file adapter.
- Reimporting a deleted annotation does not silently resurrect it. Use **Deleted annotations** and explicitly restore it.

## Fresh LLM inference

Open **Fresh LLM inference (optional)** for the selected paper. Choose OpenAI, Anthropic or Ollama and a model, then check the per-request consent box and press Generate. Consent defaults off and is cleared after a successful request.

The capability endpoint reports SDK/server-key presence for OpenAI/Anthropic. Ollama is offered through its existing localhost endpoint; availability is not a live service-health probe. Credentials are configured on the server using the existing provider mechanism, never requested or returned by the browser. No actual key values were used by development tests.

Only the selected paper's stored title (up to 2,000 characters) and abstract (up to 10,000 characters) enter the request. Personal notes, profile, uploaded documents and other papers are not included. OpenAI/Anthropic send this evidence to the chosen service and may incur costs. Fresh web calls use a 45-second transport timeout and zero SDK retries; output is bounded to 1,200 tokens where the existing transport supports it. Fresh Ollama calls bypass environment proxies and use localhost. Existing CLI/TUI provider defaults remain unchanged.

Responses become **generated / unreviewed** supplemental annotations, labelled `fresh_llm`, provider/model, language and evidence hash. Suggestions are advisory and do not establish novelty or full-text verification. Invalid output or provider failure commits no annotation, and transport errors are sanitized. This path is separate from **Extract stored metadata**, which continues to use stored assessments/local heuristics without a fresh request.

Development verification uses mocked providers for all three choices; live credentials, paid calls and actual external model responses were not exercised.

## Recovery behavior

- **Delete annotation** is a soft deletion. The content, kind, adapter, original source and all revisions remain in SQLite; the entry moves out of the active list into **Deleted annotations**. There is no permanent-purge action in this increment.
- **Restore annotation** brings the stored content/review state back and appends a revision. **Annotation version history** is paginated; restoring a historical version copies its content/review state into a new active revision without rewriting the original versions or origin metadata.
- Delete/edit/restore requests carry `expected_revision`. A stale version returns HTTP 409. Repeating deletion of an already deleted current revision, or restoring an already active current entry without a historical target, is a no-op.
- **Research note history → Restore this version** copies historical text into legacy `papers.notes` and appends a user-authored `history_restore` record. A cleared (empty) note can also be restored. `expected_note_id` guards the latest note revision; no-op same-text restores do not add duplicates.
- The confirmation explicitly states that restoring replaces the affected unsaved text/edit. Other drafts (tags, status, manual annotation form) stay intact. The note field is read-only during restoration; a response for a previously selected paper does not jump back from the user's current view.
- No library paper is deleted. CLI/TUI and old API clients continue to see the authoritative `papers.notes` field and existing ids. Two nullable `deleted_at` columns are added through the existing additive migration path; previous rows/history are retained.

## Graph interaction

Wheel over the canvas to zoom around the cursor. Existing zoom buttons and background pan remain. Drag a node to move it; incident edges follow it, and a completed drag does not act as an accidental click selection. Shift+arrow keys move the focused node; Enter/Space still select it.

Node coordinates are bounded to the canvas and stored in browser local storage per origin, database display name and seed context. This is local presentation state, not a SQLite/relationship change. Databases with identical display names on the same origin can share the layout key. Storage failure keeps the layout for the current session and shows a notice. **Reset view** resets pan/zoom; **Reset node layout** clears custom positions for that context. Pan/zoom are not persisted between section renders.

SVG export incorporates the current custom positions; GraphML/JSON keep their existing scientific data contracts. Relation directions, filters, providers and provenance are unaffected.

## API additions

| Route | Purpose |
| --- | --- |
| `GET /api/annotation-adapters` | Optional format/provider capabilities, no secrets |
| `POST /api/papers/{id}/annotations/import-files` | Bounded atomic multi-file import |
| `POST /api/papers/{id}/annotations/generate` | Explicit opt-in fresh inference |
| `GET /api/papers/{id}/annotations?deleted=true` | Paginated deleted supplemental annotations |
| `DELETE /api/papers/{id}/annotations/{annotation}` | Guarded soft deletion |
| `POST /api/papers/{id}/annotations/{annotation}/restore` | Guarded undo or historical-version restoration |
| `GET /api/papers/{id}/annotations/{annotation}/history` | Paginated version history |
| `POST /api/papers/{id}/notes/history/{revision}/restore` | Guarded append-only note restoration |

## Executed validation

- Python 3.12 with optional file adapters: **164 passed, 0 failed, 0 skipped**.
- Node/DOM regression suite: **19 passed, 0 failed, 0 skipped**.
- Restricted Python 3.11 Docker with optional file parsers installed from local wheels: **159 passed, 0 failed, 5 expected skips** — 4 Textual and 1 Node. PDF/BibTeX worker tests executed under the unchanged isolation.
- Lightweight restricted Python 3.11 Docker: **157 passed, 0 failed, 7 expected skips** — 4 Textual, 1 Node, 1 PDF and 1 BibTeX optional-dependency checks.
- Tests use synthetic upload bytes, generated PDF comments, disposable SQLite databases and mocked provider responses. Covered cases include migration from the pre-recovery schema, revision conflicts, wrong-paper ids, cleared-note restore, deletion/undo/version history, legacy JSON interoperability, repeat-safe imports, atomic rejection, malformed uploads and the stream limit.
- DOM tests cover consent, atomic multi-file request shape, draft preservation, delete confirmation/revision guards and note restoration guards. Graph tests exercise wheel math, installed pointer handlers, keyboard movement, saved layout/reset, updated edges and export geometry. jsdom is not real-browser pointer/rendering verification.
- Docker validation reused the existing local dependency image plus an offline source layer; the optional-parser profile added verified-download local wheels with `--no-index` during build under the unchanged restricted Compose settings. This is not a fresh online dependency build or a claim about remote CI.
- The visual acceptance gate was skipped by user instruction; baseline visual approval is user-provided. Windows, OCR, exact PDF highlight geometry and live provider inference remain outside the executed checks.
