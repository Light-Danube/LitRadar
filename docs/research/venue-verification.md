# Venue verification — 2026-10-15

Scope: existing OpenAlex venue lookup/search, shared CLI/browser discovery, local evidence and saved bundles. Baseline main `448a6ea0` (merged Gate 1 audit). No new provider, identity-certification or inference behavior is added.

## Executed checks

Linux Python 3.12.14, Node 24.19.0; disposable databases, synthetic worksheets and HTTP transport fixtures only:

| Command | Result |
| --- | --- |
| `python -m pytest -q -ra` with dev/web/ui/annotation dependencies | **447 passed / 0 failed / 0 skipped**; one Starlette TestClient deprecation warning |
| `npm test --prefix tests/web` | **38 passed / 0 failed / 0 skipped** across six files |
| `python -m scripts.venue_provider_probe --live` | **Failed before reaching OpenAlex:** `URLError`, proxy tunnel `403 Forbidden`; `live_search_verified: false` |
| `git diff --check` | Passed |

Live probe timestamp: **2026-10-15 01:49 Europe/Kiev** (2026-10-14 22:49 UTC). It used the production venue adapter, one explicit public lookup, timeout 8 seconds, zero retries, no API key/environment configuration or database access. The proxy refusal is environment-specific; it does not establish an OpenAlex outage or invalidate user-reported retrieval. Further live search verification remains pending.

The 17 additional tests in `tests/test_venue_verification.py` replace only `urllib.request.urlopen`, leaving HTTP request encoding, JSON parsing, venue/source/year validation, discovery transactions, CLI/API routing and file persistence active. They cover:

- Name collisions preserve distinct IDs and ISSNs; peer review/Scopus/WoS remain unverified.
- Explicit selected-source/year query, encoded Ukrainian/query punctuation and bounded page/limit survive the transport boundary.
- CLI lookup → browser search → CLI cached search returns the same canonical IDs; three separate immutable bundles are saved without repeated provider requests.
- Existing synthetic notes, tags, status, relevance score and evidence revision survive enrichment. Local artifact/worksheet reads do not initiate provider requests.
- HTTP 429/503, timeout and unavailable network at lookup/source/works stages produce classified, sanitized errors without changing library/history/cache state or leaving failed bundles.
- A provider page from a different source is rejected before any mutation.
- The probe requires `--live` and an explicit source choice for search; it never loads personal configuration or opens a library, and does not echo provider exception strings.

Existing EN/UK jsdom Research scenarios additionally verify no provider POST on page load/preset selection, draft retention through navigation/language/theme changes, conflicts, worksheets/exports and failure messages. They do not establish a live browser-provider request. Actual baseline Windows API/DOM/native Chrome results are linked in the [release checklist](../LOCAL-1.0-RELEASE-CHECKLIST.md); clean built-artifact/TUI/Narrator release checks remain separate.

## Repeat a public live probe on an allowed network

Run from the source checkout, after installing dependencies. This verification tool makes no library changes and reads no `.env`, profile, credentials or PDFs:

```sh
python -m scripts.venue_provider_probe --live --venue "Computational Linguistics"
```

Inspect returned source identities, ISSNs and type. Select a concrete identity from that bounded lookup; then replace `SOURCE_ID` below:

```sh
python -m scripts.venue_provider_probe --live --venue "Computational Linguistics" --source-id SOURCE_ID --query "context" --year-from 2023 --year-to 2026
```

The second command performs at most three requests: lookup, selected source metadata, one page of up to five works. Each request has an 8-second timeout and no retries. It uses public unauthenticated access; a provider authentication requirement is a failure to verify, not a workaround that reads credentials. Exit 0 means this particular provider probe completed; exit 1 means it failed. A successful empty search is recorded as `zero_results`, not claimed paper coverage. Preserve the JSON result, date, network and selected identity as evidence.

This probe verifies provider adapters only. It does not independently establish live browser search, every venue, complete venue coverage, peer review/index membership or scientific novelty. The user's earlier successful CLI retrieval remains user-reported evidence.
