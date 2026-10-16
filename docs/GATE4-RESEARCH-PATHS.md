# Gate 4 — Research result path safeguards

Small next slice after merged PR #30, baseline main `4dce7638`. Version stays 0.8.0. Scope: saved Research bundles, listing and allowlisted downloads; symlinks, hard-linked files and Windows reparse-point checks. Upload/restore paths and broader SQLite integrity/network-use verification remain separate Gate 4 work.

## Reproduction and fix

A disposable baseline probe reproduced acceptance of a hard-linked `search.json` referring to a synthetic file outside the Research root. The same probe is now rejected. No personal data was involved.

- Check existing path components from root to leaf with `lstat` and reject symlinks and Windows reparse attributes, including junctions on Python 3.11. Missing paths retain not-found behavior; directory link counts are unaffected.
- Require requested artifacts and manifests to be regular files with one filesystem link before returning a download path or reading manifest metadata. A linked manifest is omitted from listing and prevents downloads from that bundle. Rejected requests use existing generic API diagnostics without path/content disclosure.
- Preserve normal bundle creation, exclusive reservation, immutable export bytes, bounded filenames/sizes, selected roots and existing SQLite behavior. No files are moved, deleted or migrated by this fix.

## Executed local checks — 2026-10-16

- Independent new regression tests: **11 passed, zero failed/skipped**, Linux Python 3.12. Real hard-linked artifacts/manifests are rejected through storage/API; outside fixture bytes/mtimes stay unchanged. Root/parent/bundle/artifact/manifest symlinks and nonregular directory entries are refused. Normal listing and attachment downloads preserve immutable bundle bytes/mtimes and do not create a database.
- A simulated Windows reparse attribute blocks read/list/write through an ancestor that is not marked as a POSIX symlink. This is a stat-flag simulation, **not native Windows/junction execution**.
- Existing Research files/API/CLI tests: **74 passed, zero failed/skipped**. Full `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra`: **713 passed, zero failed/skipped**, Linux Python 3.12; one existing Starlette warning.
- `npm ci --prefix tests/web --ignore-scripts` (scratch cache), then `npm test --prefix tests/web`: **38 passed, zero failed/skipped**. No JavaScript changed. Runtime fix and independent regression tests used separate subagents.
- Changed Python syntax, **124 local documentation targets/anchors**, `git diff --check` and no-tracked-logs checks passed. Version and SQLite schema are unchanged.

GitHub-hosted Actions remain deferred by explicit user instruction because account billing blocks job startup; no CI retries, monitoring or new Windows/CI pass claim. Generated test output stays in ignored scratch directories. Application file logging remains under ignored shared `log/`; no logs are committed.

## Limits and next slice

These checks validate paths before use; they do not close every validation/use race against another local process that can replace files. Research roots through junctions/reparse points and hard-linked result files are deliberately unsupported. No complete filesystem/security audit or authentication boundary is claimed.

Gate 4's broader filesystem item remains open. Next small slice: upload/restore path safeguards with disposable fixtures; then SQLite/manual-data preservation and explicit network-use documentation in roadmap order. No personal databases, `.env`, credentials, model caches, live providers, major feature, merge, version bump, tag or release.
