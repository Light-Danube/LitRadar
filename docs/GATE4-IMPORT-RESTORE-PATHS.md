# Gate 4 — upload and restore path acceptance

Next small slice after merged PR #31, baseline main `8ca709e7`. Version stays 0.8.0. Scope: existing uploaded-byte annotation imports and new-destination restore path acceptance, using only disposable fixtures. Add focused regressions and fix only a reproduced defect; no new import/backup feature or broad filesystem rewrite.

## Verified scope

- JSON/RIS and legacy JSON imports parse the supplied payload. Absolute, Windows-style traversal and URL filenames remain display/source labels; references remain annotation metadata. In-process tests deny attempts to open an outside fixture or invoke network/provider/LLM/subprocess access. Uploaded content is imported, while outside fixture bytes/mtimes remain unchanged.
- A malformed mixed batch leaves all durable SQLite table rows unchanged, including manual notes/tags/status, annotations, revisions, deleted records and evidence. These row comparisons cover this import failure; broader provider/update integrity is still the next Gate 4 item.
- A real optional BibTeX worker preserves external file/URL fields as metadata and returns the uploaded record, without importing outside fixture content or changing its bytes/mtime. Parent-process guards do **not** cover that child. Existing optional PDF tests execute synthetic comments and reject malformed bytes; review confirms the adapter supplies `BytesIO` and no path/URL-fetch operation. No new adversarial PDF-parser certification is claimed.
- Public restore rejects symlinked/hard-linked manifests, symlinked artifact directories, hard-linked artifact files and destination-parent symlinks. Outside/source/bundle bytes and mtimes survive rejection; new destinations are absent after failure. Existing tests cover manifest traversal/drive/alternate-stream/device names, corruption/bounds, unexpected files, reparse attributes and no overwrite.
- Backup from a read-only-mode synthetic source followed by restore from a read-only-mode bundle succeeds into a new destination, preserving rows and the original additive schema without migration. POSIX mode fixtures do not establish Windows ACL behavior. Bundle checksums detect corruption, not authenticity.
- Research bundle/export traversal, symlink/reparse and linked-file checks remain covered by PR #31's regression suites. Explicit CLI `--output` paths are intentionally chosen by the local caller; they are not untrusted uploaded path labels or a browser arbitrary-path API.

No runtime defect was reproduced and no runtime/configuration/schema/version change was needed. Two subagents independently audited the upload and restore paths and added the focused tests.

## Executed local evidence — 2026-10-16

- New upload path tests: **4 passed**; new restore boundary tests: **6 passed**, zero failures/skips, Linux Python 3.12. Upload tests include the installed optional BibTeX worker. Combined new/existing recovery subset: **55 passed**.
- Existing annotation adapters, library recovery, Research files/path boundary and CLI bundle suites: **132 passed, zero failed/skipped**. Full `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra`: **723 passed, zero failed/skipped**, Linux Python 3.12; one existing Starlette warning.
- `npm ci --prefix tests/web --ignore-scripts` (scratch cache), then `npm test --prefix tests/web`: **38 passed, zero failed/skipped**. No JavaScript changed.
- Changed Python syntax, **130 local documentation targets/anchors**, whitespace and no-tracked-logs checks passed. A diff check confirms application runtime code, configuration, package/version metadata and SQLite schema are unchanged.

Hosted Actions remain deferred by explicit user instruction because account billing prevents jobs starting. No CI retries/monitoring or new Windows/CI result. Generated output stays in ignored scratch directories; application logs remain under ignored shared `log/` and are not committed.

## Limits and next slice

Together with the linked Research result checks, this closes Gate 4's filesystem checklist item for the bounded local candidate. It is not a complete filesystem/parser security audit or protection against another local process replacing files between validation and use. Optional parser workers have resource/time bounds, not a general security sandbox; only restore trusted bundles.

Gate 4 remains open. Next smallest PR: SQLite/manual-data preservation under malformed metadata, duplicate external identifiers and retryable failures; then explicit network-use documentation. No personal database, `.env`, credentials/model caches, live providers, major feature, merge, version bump, tag or release.
