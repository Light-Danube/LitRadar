# Delivery validation — 2026-10-14

Base main: `08f8ca660a093c84546c3ec4690ef85755180a68`. GitHub compare and subsequent git fetch confirmed the current checkout; GitHub search reported no open PRs before implementation. Feature branch: `codex/venue-discovery-evidence`.

## Executed local checks

- Python 3.12: `work/venv/bin/python -m pytest -q -ra -o faulthandler_timeout=30`: **298 passed, 0 failed, 0 skipped**, one Starlette/httpx deprecation warning; 6.05 seconds.
- `npm ci --prefix tests/web --ignore-scripts --cache work/npm-cache` succeeded. `npm test --prefix tests/web`: **5 passed test files, 0 failed, 0 skipped**. These are Node's reported file counts; scripts include multiple internal assertions. jsdom verifies handlers/DOM, not browser rendering.
- Changed Python modules compile; existing `web/static/app.js` syntax and `git diff --check` passed. Release stays 0.8.0.
- Default command sandbox stalled at Starlette TestClient threaded dispatch; it was interrupted. Re-running with command network permission (same source/tests; live provider calls mocked) completed successfully. This is a runtime limitation, not a claimed failed/passed browser test.
- Tests used disposable synthetic databases and fake HTTP; no production library, notes, PDFs, models, credentials or live LLM service used. Fixture integration proves canonical-state preservation and additive migration; it does not certify all real-world alias cases.

## Live checks and pending evidence

- OpenAlex Sources and Crossref Works: one unauthenticated bounded probe each; both failed with `Tunnel connection failed: 403 Forbidden`. Their API hosts are absent from the configured allowlist. No restriction bypass attempted. Live venue lookup/search, auth/API pricing and coverage remain unverified. Crossref optional enrichment is deferred.
- Literature: 20 actual records verified through accessible official records via research connectors, 5 foundations and 15 recent records through cutoff. All abstracts reviewed; three selected full-text passages. This is a bounded review, not exhaustive 2025–2026 coverage or full methodological review.
- No rendered-browser, Windows, Docker or real neural-model evaluation executed for this delivery. The browser discovery workflow is explicitly deferred; existing inbox provides the CLI handoff.
- Remote Actions results are separate from these local checks; do not infer CI success from branch publication or Draft PR creation.
