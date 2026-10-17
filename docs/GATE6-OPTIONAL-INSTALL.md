# Gate 6 — optional package installation and public guide cleanup

Draft PR #38 follows merged PR #37 (`d17c7f86`). The standard `[web]` extracted-wheel check was already green on Linux. This increment checks the documented optional `[web,ui,annotations]` install and simplifies the public README navigation. Version remains **0.8.0**.

## Reproduced package blocker and bounded fix

The first fresh optional-extras installation passed `pip check` and synthetic PDF/BibTeX parsing, but installed `LitRadarApp.run_test()` failed with `StylesheetError`: the wheel lacked `ui.tcss`. Copying that file into the *disposable diagnostic venv* made the same TUI smoke pass, isolating the packaging gap. The source stylesheet now lives in `litradar_runtime/ui.tcss`; `ui.py` resolves it beside the installed package, setuptools includes it as package data, and the setup-bundle builder requires it. The source Textual checks still use that same stylesheet.

## Executed Linux checks

- Python 3.12.14 on Linux x86_64: `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra tests/test_tui_keyboard_locales.py tests/test_user_bundle.py tests/test_project_config.py` — **31 passed**, zero failed/skipped. Full `python -m pytest -q -ra` with that scratch `PYTHONPATH` — **740 passed**, zero failed/skipped, one existing Starlette warning. After `npm ci --prefix tests/web --ignore-scripts`, `npm test --prefix tests/web` — **48 passed**, zero failed/skipped.
- Built the fixed wheel with `python -m pip wheel --no-deps --no-build-isolation --wheel-dir work/optional-verification/fixed/wheels .`, then ran `python -m scripts.build_user_bundle work/optional-verification/fixed/wheels/litradar-0.8.0-py3-none-any.whl --output-dir work/optional-verification/fixed/bundles`. The builder accepted the wheel with its required stylesheet; the ZIP contains only the wheel and `SETUP.txt`.
- Extracted the ZIP outside the checkout into a disposable directory, created a **new venv**, installed the extracted wheel `[web,ui,annotations]` plus smoke-only `httpx` through pip, and ran `pip check` — **no broken requirements**. No source-checkout or test-dependency `PYTHONPATH` was used; `cli`, `ui`, Textual, pypdf and bibtexparser imported from the venv's site-packages. Installed `litradar_runtime/ui.tcss` matched source bytes without manual copying.
- Installed-package synthetic checks passed: Textual Pilot status/feedback/tag/help and EN/UK draft flows; in-memory Unicode BibTeX/PDF parsing and bounded batch/repeat/invalid-PDF preservation; and the existing `scripts/built_wheel_smoke.py` CLI/version/defaults/static/web/edit/restart/backup/restore/checksum/history/integrity/no-overwrite/log-location path. One existing Starlette/httpx deprecation warning appeared.

The fixed scratch wheel is `litradar-0.8.0-py3-none-any.whl` (880,327 bytes; SHA-256 `e009b5728bbbe12ea94a78c5545238dce64bf9f9e84d712db7daaf56ae37a53a`). The two-file `LitBeacon-0.8.0-setup.zip` is 878,944 bytes (SHA-256 `4c18ea72c036d7973353f60698de7c71595f111ccd80d84a7802dedbaffd48d1`). Both remain in ignored scratch space and are not published. The pre-fix and fixed checks used synthetic data; no personal library, live provider or model was accessed.

## Documentation scope and remaining gate

The README now points readers to setup, recovery, Research, network, troubleshooting and optional Docker guides. The obsolete root Docker handoff moved to the historical Gate 1 archive; its index keeps the record. Current `AGENTS.md`, `ROADMAP.md` and `CODEX-HANDOFF.md` remain in the repository for maintainers. Archiving and removing landing-page links change navigation, **not** GitHub visibility or history; the two-file setup ZIP already excludes developer Markdown. The public Docker guide now matches the roadmap's local-only, optional Docker scope.

This is a Linux headless installed-package check, not native Windows/terminal, Narrator or browser evidence. Gate 6 still needs a final version-aligned 1.0.0 candidate, its own package checks, same-commit required CI/Windows smoke, release notes and explicit merge/tag/release approval. Hosted Actions remain deferred by user instruction because billing blocks job startup.
