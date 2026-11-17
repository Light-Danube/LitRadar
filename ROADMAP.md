# LitBeacon — after 1.0

LitBeacon 1.0 is public. The [completed 1.0 release roadmap](docs/archive/release-1.0/ROADMAP-1.0.md) and [verification checklist](docs/archive/release-1.0/RELEASE-CHECKLIST-1.0.md) preserve the gate evidence and its limits. No new release date or feature scope is approved here.

1. **Triage real installation and data reports.** Reproduce specific Windows, macOS or Linux failures with disposable data. Prioritize backup/restore, integrity and compatibility. Keep fixes in small Draft PRs with focused checks.
2. **Complete deferred platform verification.** Run the exact published wheel's native Windows edit/restart check and a native macOS install when those platforms are available. User-reported Windows setup, Linux package smoke and unverified macOS remain distinct evidence.
3. **Keep hosted checks current.** GitHub Actions resumed: [PR #51](https://github.com/Light-Danube/LitRadar/pull/51) passed the Python 3.11/3.12 matrix, Windows workspace, Docker and built-wheel workflows at head `4af0989b`. The Windows import suite passed 62 tests with two POSIX-only skips. This is verification of that source revision, not the exact published 1.0.0 artifact or a native macOS result. Check each subsequent PR independently.

The web workspace remains local-only. Major new features, public hosting and additional provider or model integrations need separate scope decisions and should not be treated as 1.0 defects.

Post-1.0: [explicit OpenAlex metadata-language filtering](docs/research/metadata-language-search.md), accepted with its full-text-language limitation, and [local bibliography import](docs/research/local-bibliography-import.md) are merged into source `main` (PRs #50/#51). Import supports selected RIS/BibTeX/PDF Info metadata, preview/confirmation, additive provenance and backup recovery. A small follow-up makes same-batch and saved-record conflict checks agree on publication year and author case. Automatic undo, PDF full-text/OCR and folder scanning remain deferred. A Ukrainian provider pilot requires verified endpoint/rights evidence and separate approval; JNAS NBUV is the research priority. This does not set a release date or version.
