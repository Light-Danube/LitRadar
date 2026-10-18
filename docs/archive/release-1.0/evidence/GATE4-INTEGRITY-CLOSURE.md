# Gate 4 — integrity and network-use closure

Final bounded Gate 4 slice after merged PR #32, baseline main `402a9fd6`. Version stays 0.8.0. Verify manual-data preservation through duplicate identifier refresh, malformed metadata and retryable/SQLite failures, and document existing network triggers and limits. Change runtime only for a reproduced defect; no major feature or general security-audit claim.

## Reproduced issues and bounded fixes

- Contradictory metadata could use one paper's DOI and another's provider ID: first-match lookup updated the first canonical row instead of detecting both owners. Lookup now validates all incoming identifier matches and rejects different owners before mutation. A conflicting later batch row rolls back earlier writes.
- Cross-provider DOI refresh could retain `source=openalex` while replacing its primary external ID with a Semantic Scholar ID; reopening then backfilled a fabricated OpenAlex alias. Preserve the canonical source/ID pair and add the other provider through provenance/identifier aliases. No row merge, destructive migration or automatic repair of pre-existing bad metadata.
- Legacy CLI/TUI semantic scoring instantiated SentenceTransformer without offline constraints, allowing implicit missing-weight downloads. It now uses `local_files_only=True` and `trust_remote_code=False`. Trusted local/cached models remain usable; a missing model produces an actionable message and existing caller keyword fallback. Model provisioning is a separate explicit step; no model/cache was accessed in verification.

## Executed local evidence — 2026-10-17

- Before the storage fix, the five new cases yielded **2 failed / 3 passed**: contradictory identities were accepted and cross-provider refresh corrupted the source/ID pair. After the fix, **36 focused storage/batch/citation/mixed-provider/venue cases passed**, zero failures/skips.
- The five integrity cases verify provider-ID and normalized-DOI refresh, conflicting-owner batch rollback, malformed second-row rollback and a real SQLite writer lock followed by explicit retry. Durable row/manual-field comparisons include notes/tags/status, evidence and revisions, annotations and deletion history, relations, feedback and preset tombstones. Reopen plus SQLite integrity/foreign-key checks run on disposable libraries.
- Four new mocked legacy model cases verify lazy offline-only loading/reuse, missing-model keyword fallback with safe diagnostics for both `OSError` and `ValueError`, and no model load for keyword scoring. Together with existing web semantic checks: **18 passed** as part of the final targeted run. No real model, model quality, model cache or live provider was used.
- Full `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra`: **732 passed, zero failed/skipped**, Linux Python 3.12; one existing Starlette warning. Final targeted provider/API, storage and legacy/web semantic run: **67 passed, zero failed/skipped**, including the API cases not completed in an earlier restricted-socket agent run.
- `npm ci --prefix tests/web --ignore-scripts` (scratch cache), then `npm test --prefix tests/web`: **38 passed, zero failed/skipped**. Changed Python syntax, **180 local documentation targets/anchors**, whitespace and no-tracked-logs checks passed. Version/package metadata and schema definitions are unchanged.

## Network-use review

[Network-use reference](../../../NETWORK-USE.md) identifies destinations, payloads, explicit and previously enabled scheduled triggers, cache behavior, Telegram delivery, cloud/local LLM differences, downloads/browser links and installation/model provisioning. The shipped web assets require no external CDN; no mandatory telemetry sender was found in the reviewed application paths. This is a scoped source review, not a claim about third-party SDKs, installers, browser extensions or arbitrary model servers.

## Closure limits

Combine this record with [loopback launch](GATE4-LOCAL-BOUNDARY.md), [Research result paths](GATE4-RESEARCH-PATHS.md) and [upload/restore acceptance](GATE4-IMPORT-RESTORE-PATHS.md). Gate 4 closure is for the bounded local candidate, not a complete security audit, proof against hostile local filesystem races or release approval. Existing library metadata is not audited/repaired, and live provider availability/model quality are not established.

Hosted Actions remain deferred by explicit user instruction because account billing prevents job startup; no CI retries/monitoring or new Windows pass. New/extended application logs remain under ignored shared `log/`; scratch output and logs are not committed. Version stays 0.8.0. No personal database, `.env`, credentials/model-cache access, major feature, merge, version bump, tag or release. Next vertical step is Gate 5's existing keyboard/usability evidence, followed by Gate 6 release packaging/approval.
