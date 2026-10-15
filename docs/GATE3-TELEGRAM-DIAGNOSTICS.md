# Gate 3 increment — Telegram listener diagnostics

Baseline main `044358b8` (merged #26). Gates 1–2 are complete; this is one focused Gate 3 increment, not full Gate 3 or release approval. Version remains 0.8.0.

Planned scope:

- Stop the optional long-poll listener with a clear nonzero CLI result on Telegram HTTP 409, rather than retrying competing pollers indefinitely. Keep transient retry, Ctrl+C, nonfatal menu setup and existing offsets.
- Explain common Telegram failures (400/401/403/404/409/429/5xx, timeout/network/invalid response) with bounded actionable messages. Do not copy remote bodies, token-bearing URLs, credentials, chat/message content or raw exception text into diagnostics.
- Provide timestamped listener diagnostics and opt-in local debug/file logging with documented limits; preserve scheduled digest behavior. Avoid a broad provider or application logging rewrite.
- Exercise fake HTTP/API failures and credential-safe logging, including Windows CI. No live credentials, personal databases, major features, version bump, merge or release.

Implementation and test results are pending. Scheduler disable/remove and full provider-failure/local-workspace verification remain separate Gate 3 work.
