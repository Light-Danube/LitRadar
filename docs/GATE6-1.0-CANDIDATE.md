# Gate 6 — Draft 1.0.0 installation candidate

Draft PR #39 starts from merged main `d3bb5513` (PR #38). **1.0.0 is candidate source/package metadata, not a published release.** Published v0.8.0 remains available. The candidate is for [fresh-folder Windows/macOS/Linux installation testing](PACKAGE-SETUP.md); it does not authorize merge, tag or publication.

## Executed Linux checks

On Linux x86_64 with Python 3.12.14, from the candidate tree:

- `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra`: **740 passed, zero failed/skipped**, one existing Starlette/httpx deprecation warning. `npm ci --prefix tests/web --ignore-scripts` then `npm test --prefix tests/web`: **48 passed, zero failed/skipped**. Tests use disposable/synthetic data.
- `python -m pip wheel --no-deps --wheel-dir work/v1-install/wheels .` and `python -m scripts.build_user_bundle work/v1-install/wheels/litradar-1.0.0-py3-none-any.whl --output-dir work/v1-install/bundles` succeeded. Wheel: **63 entries**, including `litradar_runtime/ui.tcss`; filename inventory found no `.env`, SQLite, PDFs, logs, pyc/cache or `work/` paths. ZIP: exactly the wheel and `SETUP.txt`, with byte-identical wheel content. The builder also validates wheel metadata against root/bundled VERSION and pyproject.
- Extracted the ZIP outside the checkout, created a new venv, installed the **extracted** wheel `[web,ui,annotations]` plus smoke-only `httpx`, then ran `pip check`: **no broken requirements**. `python -m cli --version` reported `LitBeacon 1.0.0`.
- With a disposable `LITBEACON_HOME`, the installed `scripts/built_wheel_smoke.py` passed CLI/defaults/static-assets/web edit and reopen, synthetic backup/new-destination restore, checksums, histories, SQLite integrity, no overwrite and `log/` location. A separate installed-package check confirmed distribution and bundled version metadata, FastAPI OpenAPI version, web `v1.0.0` label and Textual Pilot startup. No checkout import, personal library, live provider or model was used.

Scratch artifacts are **not published**: `litradar-1.0.0-py3-none-any.whl` — 880,318 bytes, SHA-256 `3897d5175bddb2b8edac73b0e4a04776651525f274741369a6fa3345dd8bdf36`; `LitBeacon-1.0.0-setup.zip` — 879,038 bytes, SHA-256 `fdf6bf0c7ce2d13d6111d2a0fddc84a26fa59558fb625c78de1a55495ceb2e24`. Hashes identify this local build, not a future published asset or signature. The installed smoke uses headless FastAPI/TestClient and Textual Pilot, not a native browser/terminal.

## Open platform and release checks

- **Windows:** the user attempted GitHub's source ZIP, not a built setup ZIP, and reported `dataclass(slots=...)` failing; the exact Python version and first pip failure are unavailable because the batch window closed. [Draft PR #40 source-ZIP repair and steps](WINDOWS-SOURCE-ZIP.md) address interpreter choice, broad dependencies and visible errors, but a native retest is pending. Earlier Windows installed-wheel checks were on older commits; Linux success does not imply a Windows pass.
- **macOS:** no macOS runner or user machine was available. Python/CPU dependency wheels, TUI and browser behavior remain unverified. The guide gives commands but makes no compatibility claim.
- **Linux:** this one Python 3.12 x86_64 environment passed; other distributions/Python versions and native browser appearance remain unverified.
- **Required CI:** hosted GitHub Actions are deferred by user instruction because account billing blocks job startup. Do not retry/monitor jobs, change billing/workflows or claim same-commit CI. The final candidate needs required checks on the same reviewed commit when available.
- **Release decision:** review fresh-install feedback and any fixes, check version/artifact again on the final commit, then obtain explicit approval before merge/tag/release. Publishing a release would trigger the existing artifact-attachment workflow; this Draft PR does not publish one.

Known product limits for the release note: web binds to localhost and has no authentication for LAN/public hosting; provider searches, dependency installation, optional Telegram and explicitly selected cloud LLMs can use the network; venue metadata is not indexing/peer-review/novelty proof; optional local semantic work is off by default. Source-checkout and wheel data locations differ. See [network use](NETWORK-USE.md), [user guide](USER-GUIDE.md) and [recovery](USER-GUIDE.md#consistent-local-backup-and-restore-unreleased).
