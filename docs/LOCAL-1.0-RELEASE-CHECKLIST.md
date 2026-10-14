# Local-only LitBeacon 1.0 — Gate 1 audit

Audited 2026-10-15 against main [`b8b42ff4`](https://github.com/Light-Danube/LitRadar/commit/b8b42ff4b348dce82df353b6bf01856cbfd7e3ba). Application version remains **0.8.0**. This is an inventory and release checklist, not release approval. No major features, migrations or personal-data operations are introduced.

## Frozen feature inventory

| Existing behavior | Implementation / regression evidence | Verification boundary |
| --- | --- | --- |
| Original five web sections: overview, literature, graph, clusters, jobs; sixth Research section | `workspace_web.py`, `web/static/app.js`, `web/static/research-workspace.js`; `tests/test_workspace_workflow_smoke.py`, `tests/web/workflows.cjs`, `tests/web/research.cjs`; [48 preservation contracts](ux-research/feature-parity.md) | Synthetic API/DOM checks; Windows native browser subset below |
| Inbox edits, notes/tags/status, relevance feedback, exports, local offline bundles | `storage/sqlite.py`, `bibliography.py`, `offline.py`; storage, sorting/tags, bibliography/offline and workflow tests | Synthetic data; real PDFs and personal library excluded |
| Citation direction/provenance, provider/year filters, layout/gestures, SVG/GraphML/JSON export; heuristic clusters | `citation_intelligence.py`, `web/static/graph-*.js`; mixed-provider, graph and frontend tests | Native Windows graph scenarios observed; no novelty/quality claim |
| EN/UK web and TUI, theme/navigation/draft preservation, keyboard and worker error recovery | `web/static/locales.js`, `theme.js`, `ui.py`, `ui_locales.py`; shell, Research, UI workflow/localization tests | Automated fixtures pass; Narrator/manual TUI audit pending |
| Annotation imports/edit/review, soft delete/undo, guarded note/history restoration | `web/annotation_actions.py`, `web/file_adapters.py`, `storage/sqlite.py`; annotation adapter/recovery tests | Optional parsers installed locally; providers mocked; history recovery is not database restore |
| Explicit venue lookup/search, editable presets, guarded evidence worksheets, immutable local result bundles | `venue_discovery.py`, `storage/evidence.py`, `storage/venue_presets.py`, `web/research_api.py`, `web/research_files.py`; venue/evidence/Research tests | EN/UK drafts/conflicts and no provider POST on load/preset selection covered in `tests/web/research.cjs`; snapshot failures report saved SQLite state |
| CLI/TUI, scan/digest/jobs and optional Telegram | `cli.py`, `research_digest.py`, `telegram_bot.py`; CLI, schedule, Telegram and UI tests | Scheduler, downloads and services mocked; duplicate real listeners need Windows smoke |
| Optional local semantic exploration and explicit fresh LLM inference | `ranking/semantic_workspace.py`, annotation actions; semantic/API and shell tests | Experimental semantic feature stays off by default; no weights downloaded or live LLM called; neural quality evaluation is not a 1.0 blocker |

User-reported acceptance remains separate: WebUI visual/functionality accepted and extra cloud-browser gate waived on 2026-10-14; live CLI retrieval reported working locally. Neither is an independently executed live-provider check.

## Executed evidence

Local Linux, Python **3.12.14**, Node **24.19.0**, tracked-source export of the audited commit (no `.env` or personal database copied):

| Command | Result |
| --- | --- |
| `python -m pytest -q -ra` with dev/web/ui/annotation requirements installed | **430 passed / 0 failed / 0 skipped**, 24.67s; one Starlette TestClient deprecation warning |
| `npm ci --prefix tests/web --ignore-scripts --cache <disposable-cache>` then `npm test --prefix tests/web` | **38 tests passed / 0 failed / 0 skipped** across six files; completed with subprocess/socket permission |
| `python -m pip wheel --no-deps --no-build-isolation --wheel-dir <scratch>/wheels .` | Built `litradar-0.8.0-py3-none-any.whl`; construction succeeds, installed CLI fails as described below |
| `python -m pip install --no-deps --target <scratch>/wheel-installed <wheel>`; outside source tree, `PYTHONPATH=<installed-wheel>:<test-deps> python -c 'import cli'` | **Failed:** `ModuleNotFoundError: No module named 'config'` |
| Wheel ZIP inventory | `config.py`, `VERSION` and default JSON files absent; web static assets present; no `.env`, SQLite or PDF entries found (limited inventory, not full artifact audit) |
| `git diff --check` | Passed for checklist/documentation changes |

Initial dependency setup failed inside the restricted executor (proxy socket access; npm cache location). Resolved using network permission and a scratch npm cache. Initial restricted Python attempts stalled and were terminated; an initial Node report counted only six files. The completed runs above establish the suite results. Tests used synthetic/disposable fixtures; no live-provider/model or personal-data validation.

Actual GitHub checks at audited main all succeeded; these are **baseline results, not the new Draft PR's checks**:

| CI profile | Executed result / explained skips |
| --- | --- |
| [Core/UI/web, Python 3.11 and 3.12](https://github.com/Light-Danube/LitRadar/actions/runs/38645380535) | Each version: core 340 passed / 34 skipped (6 browser-module skips, 28 Textual cases); UI 368 / 6 (browser modules); web 402 / 28 (Textual); Node 38 passed / 0 failed / 0 skipped |
| [Isolated Docker](https://github.com/Light-Danube/LitRadar/actions/runs/38645380689) | 399 passed / 0 failed / 31 skipped (28 Textual, PDF/BibTeX adapters, Node) |
| [Windows Python 3.12 / native Chrome](https://github.com/Light-Danube/LitRadar/actions/runs/38645380577) | Targeted Python 129 passed / 0 failed / 1 skipped (POSIX permissions); Node 38/0/0; four sandboxed Chrome EN/UK desktop/narrow scenarios passed |

No open PRs or issues were returned before this audit PR was created. PRs [#18](https://github.com/Light-Danube/LitRadar/pull/18), [#19](https://github.com/Light-Danube/LitRadar/pull/19), [#20](https://github.com/Light-Danube/LitRadar/pull/20) are merged; old feature-branch names do not establish pending work. Historical Docker fake-`gh` failures at `a9152bb1` ([run](https://github.com/Light-Danube/LitRadar/actions/runs/38470366811)) are superseded by the successful current run. No current full-suite regression was reproduced; the wheel failure is a separate release blocker.

## Release checklist — keep remaining gates open

- [x] **Gate 1 inventory/backlog:** freeze implemented workflows; no open feature PR to reconcile at audit time.
- [x] **Gate 1 source regressions:** combined Python/JS pass, Research and five-section EN/UK/draft/consent contracts covered by synthetic tests; dependency skips explained by CI profile.
- [x] **Gate 1 audit candidate CI:** actual checks at merged audit PR #21 head `84c3f5ed` succeeded. This does not establish later packaging/recovery/release-candidate checks.
- [ ] **P0 packaging defect (Gates 3/6):** explicit `pyproject.toml` module list omits `config.py`, which `cli.py` imports. CLI also reads sibling `VERSION`; profile/digest defaults are sibling JSON files, absent from the wheel. Add a focused packaging fix and clean installed-artifact CLI/web smoke outside the checkout; verify package-owned assets and writable user-data paths.
- [x] **P0 recovery source checks (Gate 2, unreleased):** `library-backup` uses a read-only source/SQLite backup API; `library-restore` validates manifests/checksums, integrity/foreign keys and paths into a new directory only. Elected Research/offline files require stopped-writers acknowledgment; profile/config/scheduler recovery stays manual. CLI `restore` retains paper-status behavior. See [instructions](USER-GUIDE.md#consistent-local-backup-and-restore-unreleased); final CI/Windows artifact checks remain open.
- [x] **P0 upgrade integrity source checks (Gate 2):** synthetic older metadata schema restored/upgraded twice with stable identities/manual fields/history and successful integrity/foreign-key checks. Existing v0.1 migration fixture remains covered separately; no personal database migrated.
- [ ] **P0 Windows install/use (Gate 3):** built-artifact clean install, launcher/update, CLI/TUI, offline persistence/exports, scheduler disable/remove and duplicate-listener checks. Existing Windows browser source-checkout tests cover only a subset.
- [ ] **P0 local boundary (Gate 4):** retain localhost default and executed traversal/symlink/upload/dedup regressions; record a focused offline/provider-failure smoke. No public hosting/authentication work or complete-security-audit claim.
- [ ] **P1 practical accessibility (Gate 5):** execute Windows Terminal + Narrator fixture/manual check; document blocking keyboard/assistive limitations honestly.
- [ ] **P0 release artifact/docs (Gate 6):** clean installation, full artifact exclusions, backup/upgrade guide and final candidate checklist. Keep 0.8.0 until candidate verification and explicit release approval; no merge/tag/version bump in this PR.

**Gate 1 is not declared complete:** candidate CI remains open; reproduced packaging failure is fixed locally, while Windows built-artifact and other release gates remain unverified. Real-model evaluation and optional Docker production optimization are outside the frozen 1.0 release scope, despite older handoff language.

[Further venue verification](research/venue-verification.md): **447 Python / 38 JS passed, 0 failed, 0 skipped** on a dedicated branch, with additional HTTP-transport CLI/API identity/filter/preservation tests. Explicit live lookup encountered the cloud proxy tunnel 403 before OpenAlex. A repeatable public probe is available; live search remains pending. User-reported working retrieval is not promoted to an independently observed pass.

## Smallest next PR — local recovery, not a new subsystem

Recommend **`fix(recovery): consistent local backup and restore to a new destination`**: one bounded recovery module, two explicit CLI operations and USER-GUIDE instructions; no new UI/provider/schema/workspace subsystem.

1. Open the selected SQLite source directly read-only and use SQLite's backup API, avoiding `PaperStore` startup migrations on the source. Produce a private, exclusively reserved bundle with versioned manifest, relative paths, sizes and SHA-256 checksums. Never raw-copy a live database/WAL set.
2. Include only explicitly elected `research/` bundles and offline artifacts. Require writers stopped when including filesystem artifacts: SQLite backup cannot atomically snapshot separate mutable files. Record exclusions and requirements for scheduler/profile configuration; exclude `.env`, credentials, caches and logs.
3. Validate bounds, checksums, SQLite `integrity_check`/`foreign_key_check` and paths before publishing. Restore only into a new disposable destination; reject occupied destinations, traversal, symlinks, duplicate paths, missing files and corrupt manifests. Never overwrite or silently merge.
4. Synthetic acceptance tests: committed snapshot with active WAL; round-trip notes/tags/status/IDs, citations/feedback, annotation/evidence revisions and tombstones; elected artifacts; corrupt/missing/duplicate-path rejection; injected failure cleanup; restored legacy database upgrade twice with stable IDs/history and integrity checks. No services/models/personal data.

Implemented in the focused `codex/local-backup-restore` increment: Linux Python 3.12.14 recovery **49 passed / 0 failed / 0 skipped**; full branch `python -m pytest -q -ra` **479 passed / 0 failed / 0 skipped**, one Starlette warning; `npm test --prefix tests/web` **38 passed / 0 failed / 0 skipped**. Evidence includes committed active-WAL/source-schema preservation, exact all-table round-trip including histories/tombstones, elected files, unsafe manifests/SQL schemas, damage/missing/duplicates, bounds and injected-error cleanup, then repeated additive legacy upgrades. Packaging remains a separate defect PR. A disposable integration checkout combining the packaging/recovery/venue code passed **501 Python tests**, and its installed wheel passed CLI backup/restore/no-overwrite, exact all-table preservation, elected files and browser evidence/artifact-download smoke outside the checkout. This Linux integration test does not establish recovery-head CI or Windows installed-artifact recovery; these remain pending. No personal-library drill or release approval is implied.
