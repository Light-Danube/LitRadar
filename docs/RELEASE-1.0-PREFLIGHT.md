# LitBeacon 1.0 release preflight

This is the maintainer's final check for the **tagged but unpublished 1.0.0 candidate**. PRs #43 and #44 are merged, and the requested `v1.0.0` tag points to `da4486ab`. The user reported a successful standard-user install of the two-file Windows setup ZIP. The GitHub Release and its assets remain pending; [the active checklist](LOCAL-1.0-RELEASE-CHECKLIST.md) records the exact local build and limitations. The GitHub source ZIP is a separate install path.

## Prepare the exact artifacts

From a clean, reviewed checkout at the commit intended for the release, record `git rev-parse HEAD` and confirm `git status --short` is empty. Use Python 3.12. In a new `dist/` directory:

```sh
python -m pip wheel --no-cache-dir --no-deps --wheel-dir dist .
python -m scripts.build_user_bundle dist/litradar-1.0.0-py3-none-any.whl --output-dir dist --tag v1.0.0
```

The bundle builder checks VERSION, pyproject metadata, bundled VERSION, required runtime files, excluded local-data paths and the tag string. The actual `v1.0.0` Git tag was separately verified to point at `da4486ab`; the builder alone does not prove that. Confirm the ZIP has exactly `litradar-1.0.0-py3-none-any.whl` and `SETUP.txt`, and record SHA-256 of both files. Never copy `.env`, `data/`, `log/`, PDFs, caches or the full checkout into the release download.

Extract the ZIP into a fresh folder **outside the checkout** and follow [the package guide](PACKAGE-SETUP.md) on each available platform. On Windows, use `py -3.12`, install the **extracted wheel**, run `pip check` and `-m cli --version`, initialize a disposable `LITBEACON_HOME`, open the local web page, edit a synthetic paper, restart and confirm persistence. Stop with Ctrl+C. Keep the result distinct from the already user-tested source-ZIP launcher. On Linux/macOS, use the corresponding guide; record the Python/OS version and exact failures. Never point these checks at a personal library.

## Release decision and upload

Record the exact commit, artifact hashes, platform results, unresolved limitations and approval in the active checklist. Hosted Actions currently cannot start because of account billing; a green check is not inferred. If required CI remains unavailable, Gate 6 stays open unless the owner explicitly accepts that exception. macOS has no native result yet; describe that limit in the release notes rather than claiming support was verified.

Create a draft GitHub Release for the existing `v1.0.0` tag, attach both verified files, and check that the draft shows both assets before publishing. Recheck the public download links and hashes after publication. The current release workflow runs only on `release: published`; it cannot supply an asset before publication while Actions are blocked. If it later runs, compare public asset hashes with the verified files. The current GitHub connection cannot upload release assets, so this step requires a maintainer with GitHub release access and the exact files.

## Proposed 1.0 release notes

LitBeacon 1.0 is a local-only research workspace with a browser interface, CLI, optional Textual TUI and Telegram workflows. Since v0.8.0 it adds local library backup/restore and recovery checks, Research venue search and evidence worksheets, annotation/graph/usability refinements and optional, off-by-default local semantic exploration. Existing LitRadar module names and data paths remain compatible. Install from the two-file setup ZIP with Python 3.12; dependency installation and explicit scholarly/provider requests need network access. The browser binds to localhost and is not intended for public/LAN hosting. Back up before upgrading; an installed wheel does not automatically move a source-checkout library. See [setup](PACKAGE-SETUP.md), [backup/upgrade](USER-GUIDE.md#consistent-local-backup-and-restore-unreleased) and [network use](NETWORK-USE.md).

Release notes must include the final platform test record. The user reported both a successful standard-user source-ZIP retest after the pip-cache change and a fresh-folder Windows install of the separate two-file setup ZIP without administrator rights; the package web workspace started and showed v1.0.0. A Linux Python 3.12 package smoke and 740 Python / 48 JavaScript local tests passed. Native Windows package edit/restart persistence and macOS installation were not confirmed by the user's report. Same-commit GitHub Actions remain blocked before job startup by account billing. No release is published by this document.
