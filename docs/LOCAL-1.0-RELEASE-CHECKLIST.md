# LitBeacon 1.0 release checklist

Source `main` contains the unreleased 1.0.0 candidate through merged PR #43 (`86f20a68`). Published v0.8.0 remains the current release. [Detailed development checks and PR history](archive/release-1.0/RELEASE-CHECKLIST-development.md) are archived; this page tracks the remaining release decision.

- [x] **Gates 1–5:** feature stability, synthetic and earlier Windows recovery checks, local boundary, and keyboard/ordinary-use evidence are complete for the bounded candidate. [Roadmap and limits](../ROADMAP.md) · [validation archive](archive/release-1.0/README.md).
- [x] **Linux candidate package:** Python 3.12 local suites passed **740 Python / 48 JavaScript**, zero failures/skips, with one existing Starlette warning. The two-file setup ZIP contained a byte-identical 63-entry wheel and `SETUP.txt`, excluded local data, and its extracted `[web]` wheel passed fresh Linux `pip check`, version, synthetic CLI/web edit/restart and recovery smoke. These checks ran before this documentation-only branch.
- [x] **Windows installation, user-reported:** the PR #43 source ZIP launched without administrator rights. The user separately built its two-file 1.0 setup ZIP, extracted it into a fresh folder, followed the package guide without administrator rights, and reported that web opened showing v1.0.0. This report does not establish package edit/restart persistence or an artifact hash.
- [ ] **Final package checks:** record final-commit artifact hashes and, if possible, complete native Windows package edit/restart persistence. Native macOS installation has no result; label it unverified rather than claiming compatibility.
- [ ] **Required CI:** hosted GitHub Actions cannot start because of account billing. No green same-commit CI result exists. A release with this exception needs an explicit owner decision.
- [ ] **Release:** review final notes and package, obtain explicit approval, then tag and publish with both verified assets. No v1.0.0 tag, release or public setup ZIP exists yet. [Maintainer preflight](RELEASE-1.0-PREFLIGHT.md).

No personal library, credentials or live provider is needed for these checks. User-reported Windows results and executed Linux/older Windows automation are distinct forms of evidence.
