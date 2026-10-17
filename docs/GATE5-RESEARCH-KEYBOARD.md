# Gate 5 — Research browser keyboard journey

Draft PR #36 checks the existing English/Ukrainian Research flow from the sidebar through venue choice, evidence editing and saved comparison download. It follows merged PR #35 on `main` (`be81f40a`). The check uses synthetic responses and disposable page state; no live scholarly request or personal library is involved.

## Reproduction and change

Existing DOM tests reached the path through direct clicks and form submission, but did not check focus. Two new EN/UK journeys failed on the merged baseline, each finding seven focus gaps: entering Research, receiving venue choices and search results, opening evidence, returning from save/reload, and reaching a new export download. The existing source choice already focused the search query.

The browser now focuses the venue query on explicit Research navigation, the first venue choice after lookup, the first paper selector after a nonempty search, the first evidence field when a sheet opens, and the newly saved Markdown download after export. An empty search focuses the results section. Save/reload rebuild the worksheet while keeping its focused control, open field groups and text selection. Async responses must not pull focus from another control, locale view or paper. A failed action retains drafts and leaves its trigger recoverable.

All online lookup and search requests still require explicit submit. Venue identities, paper selection and worksheet values still require user review. Export reads the saved worksheet rather than unsaved editor text. This PR changes browser focus behavior only; it adds no provider, schema or storage workflow.

## Local evidence and limits

The two new EN/UK jsdom journeys use synthetic API responses and explicitly model browser Enter/Space activation. Their original baseline was **0 passed / 2 failed** with seven focus handoff failures in each locale. Two further cases cover a late lookup/language change and a pending evidence save while the user edits an expanded field or opens another paper. Candidate: **4 new cases passed**, zero failed/skipped. The existing Research DOM checks cover error/draft/conflict behavior.

Full local candidate on Linux Python 3.12: `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra` — **740 passed**, zero failed/skipped, one existing Starlette warning. After `npm ci --prefix tests/web --ignore-scripts` with the scratch cache, `npm test --prefix tests/web` — **48 passed**, zero failed/skipped. Changed JavaScript syntax and whitespace checks passed. No backend, schema, dependency lockfile or version change.

jsdom does not prove native Tab order, rendered scrolling, physical key activation, actual downloads, Windows/Narrator behavior or a participant's ability to discover the workflow. The user previously accepted the Web UI visually and reported Windows/Narrator daily use; those are separate evidence. Ordinary-user observation remains the open Gate 5 item. Hosted Actions remain deferred by user instruction because billing blocks job startup. Version stays 0.8.0; no personal database, live provider, merge, version bump, tag or release is involved.
