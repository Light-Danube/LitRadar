# LitBeacon — after 1.0

LitBeacon 1.0 is public. The [completed 1.0 release roadmap](docs/archive/release-1.0/ROADMAP-1.0.md) and [verification checklist](docs/archive/release-1.0/RELEASE-CHECKLIST-1.0.md) preserve the gate evidence and its limits. No new release date or feature scope is approved here.

1. **Triage real installation and data reports.** Reproduce specific Windows, macOS or Linux failures with disposable data. Prioritize backup/restore, integrity and compatibility. Keep fixes in small Draft PRs with focused checks.
2. **Complete deferred platform verification.** Run the exact published wheel's native Windows edit/restart check and a native macOS install when those platforms are available. User-reported Windows setup, Linux package smoke and unverified macOS remain distinct evidence.
3. **Restore hosted checks when available.** GitHub Actions jobs currently cannot start because of account billing. Re-run relevant checks once that account constraint is resolved; do not infer a pass from pending or canceled runs.

The web workspace remains local-only. Major new features, public hosting and additional provider or model integrations need separate scope decisions and should not be treated as 1.0 defects.

Post-1.0 Draft PR: [explicit OpenAlex metadata-language filtering](docs/research/metadata-language-search.md), accepted with its full-text-language limitation. Local bibliography import remains a separate design; a Ukrainian provider pilot requires verified endpoint/rights evidence and separate approval. This does not set a release date or version.
