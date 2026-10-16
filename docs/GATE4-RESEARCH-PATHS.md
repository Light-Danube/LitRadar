# Gate 4 — Research result path safeguards

Small next slice after merged PR #30, baseline main `4dce7638`. Version stays 0.8.0. Scope: saved Research bundles, listing and allowlisted downloads; symlinks, hard-linked files and Windows reparse-point checks. Upload/restore paths and broader SQLite integrity/network-use verification remain separate Gate 4 work.

A disposable baseline probe reproduced acceptance of a hard-linked `search.json` referring to a synthetic file outside the Research root. No personal data was involved. Local implementation and independent regression results will be recorded after execution. GitHub-hosted Actions remain deferred by explicit user instruction because account billing blocks job startup; no CI retries, monitoring or pass claim.
