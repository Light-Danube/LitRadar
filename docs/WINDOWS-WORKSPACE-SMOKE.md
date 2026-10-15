# Windows workspace workflow validation

Current evidence: actual [Windows API/DOM/native Chrome run](https://github.com/Light-Danube/LitRadar/actions/runs/38651164554) succeeded, including recovery/legacy upgrade (**49 passed, 1 case-insensitive-filesystem skip**) and four sandboxed EN/UK desktop/narrow Chrome scenarios. [Clean installed-wheel Ubuntu/Windows smoke](https://github.com/Light-Danube/LitRadar/actions/runs/38656486258) also succeeded. Later setup-package candidates require their own checks.

On **2026-10-15 the user confirmed Windows daily use and Narrator work okay**. This is accepted as user-reported evidence; exact Windows/terminal/reader versions and detailed task observations were not supplied. Narrator is optional. This is separate from synthetic CI and does not imply certification or a reproduced real scheduler/token test.

The `Windows workspace smoke` GitHub Actions workflow uses `windows-latest`,
Python 3.12 and Node 22. It runs on pull requests, `main`/`codex/**` pushes,
and manual dispatch. A workflow definition is not evidence of a passing run:
review its actual Windows job result before marking Windows verification complete.

All workflow data are synthetic. Python uses disposable SQLite databases and
FastAPI TestClient; provider fetches are mocked. Node uses jsdom and the actual
production scripts with a local synthetic API fixture. No production database,
credentials, scheduler installation, fresh LLM call or embedding model download
is involved. Dependency installation requires the package registries; tests do
not request provider services.

The smoke checks cover:

- Inbox search, editing notes/status/tags, durable API readback and note history.
- Tag-based cluster membership and opening a cluster paper in the real DOM.
- Opening a paper's seeded graph, selecting/recentering a node and returning to
  its detail pane, in both English and Ukrainian.
- Mixed OpenAlex/Semantic Scholar aliases, duplicate response records, rejected
  self edges, antiparallel citations, two-hop cycles, provenance and cache refresh.

To reproduce in PowerShell from the repository directory:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt -r requirements-web.txt -r requirements-annotations.txt
.venv\Scripts\python -m pytest -q tests/test_workspace_workflow_smoke.py tests/test_citation_mixed_providers.py tests/test_workspace_web.py tests/test_workspace_v08.py
npm ci --prefix tests/web --ignore-scripts
npm test --prefix tests/web
```

jsdom exercises DOM events and API contracts; it does not render pixels or prove
browser layout/accessibility. Native browser rendering and manual interaction
remain distinct from this reproducible workflow smoke suite.

## Native Chrome check

The job also installs test-only `requirements-browser-tests.txt` and runs
`python -m scripts.windows_browser_smoke` using the runner's installed Chrome
with sandbox enabled and a fresh repository-local profile. It exercises EN/UK
at 1440×900 and 390×844, actual inbox saves, cluster/detail navigation, ordinary
mouse-click node selection, dragging, wheel zoom and export-menu Escape. A
synthetic SQLite database is created under ignored `.venv/`; no personal data,
real scheduler, provider/model or external browser request is used. Only the
four generated PNGs are uploaded as short-lived artifacts, not the profile/DB.

Earlier cloud Chromium could not start its sandbox, but actual sandboxed Windows
Chrome scenarios have since succeeded in the linked Actions run. This does not
claim a cloud-browser pass or an exhaustive visual/accessibility audit.
The Node test command uses explicit file paths to avoid relying on Windows
shell wildcard expansion.
