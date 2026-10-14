# Windows workspace workflow validation

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

The native script was syntax-checked here but **not executed**: the cloud
Chromium sandbox limitation persists. Its actual Windows result is a release
gate. A configured CI step or Linux DOM result is not a native Chrome pass.
The Node test command uses explicit file paths to avoid relying on Windows
shell wildcard expansion.
