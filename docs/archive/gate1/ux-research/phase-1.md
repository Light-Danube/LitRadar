# Quiet Research — Phase 1, implementation and review

Date: 2026-10-13. Base: `main` at `3df12b79` (research PR #8 merged).
Branch: `codex/web-redesign-shell`. This is an implementation candidate, not a final design decision.

## Component plan and implemented scope

1. Replace fragmented dark colors with semantic light/dark tokens for canvas, surfaces, text, borders, controls, alerts and focus; share spacing, type and radius tokens.
2. Apply theme before CSS via a small local script. Appearance offers System / Light / Dark in English and Ukrainian. Store only `litbeacon-theme`; default to OS preference, with light fallback. A previous user without a preference may see light when their OS is light. Explicit Dark remains available. Storage failures do not block startup.
3. Keep all five destinations visible. Desktop uses a sidebar; below 760px navigation wraps into two columns, header controls wrap and content stacks. Group each form label with its field. Improve text hierarchy, normal-text readability and primary save/apply actions.
4. Use the same semantic palette for on-screen graph labels, edges and nodes. Standalone SVG exports retain their existing self-contained dark fallback. Citation direction, dashes, provenance and export payloads are unchanged.
5. Preserve focus, selected work, unsaved forms and graph viewport when changing appearance: theme changes update the root attribute, never the page renderer. Existing locale switching and shortcuts remain intact.

No new production dependency, build system, API, schema, Docker/security setting, external font or CDN. `tests/web` has a locked **test-only** jsdom dependency to exercise the real HTML and scripts with synthetic, in-memory API responses. Production remains vanilla JS served by Python.

## Executed verification

| Command / check | Result |
| --- | --- |
| `.venv/bin/python -m pytest -q -ra` (Python 3.12) | 144 passed, 0 failed, 0 skipped; one existing Starlette/httpx deprecation warning |
| `npm ci --prefix tests/web --ignore-scripts` then `npm test --prefix tests/web` | 11 passed, 0 failed, 0 skipped (6 dependency-free tests + 5 DOM integration tests) |
| `node --check` for app, locales, graph-tools, theme | Passed |
| `git diff --check` | Passed |
| Secure Playwright / system Chromium launch | Failed before rendering: SUID sandbox helper configuration; no screenshots or visual pass |

The first DOM run exposed incomplete synthetic graph/cluster response fixtures; their shapes were corrected to match the existing API. No application validation was weakened. No skipped tests in the executed suites. Optional dependencies were available locally; other CI combinations have not been run here.

The DOM tests exercise saved/system/invalid/blocked-storage themes, OS changes, EN/UK labels and `html.lang`, note/status/tag PATCH, annotation drafts, all five Alt shortcuts, `/` search, graph Enter selection and preservation of its viewport. Token tests calculate WCAG contrast (text 4.5:1, controls/focus 3:1 on intended surfaces). This is not a full WCAG conformance claim. jsdom cannot validate reflow, native keyboard Tab order, browser zoom, pointer geometry or screenshots.

## Feature parity review

All 48 rows in [feature-parity.md](feature-parity.md) remain the acceptance checklist. No feature was intentionally removed or backend contract changed. Review of the application diff covers all rows; it does **not** mean 48 separate browser scenarios passed.

| Contracts | Evidence and limits |
| --- | --- |
| F01–F05 | DOM navigation, locale, shortcuts; existing skip/live/busy/connection controls retained. Visual focus and screen-reader announcements still need real-browser review. |
| F06–F16 | Existing summary/library/search/detail handlers retained; DOM opens a synthetic paper; Python tests cover API search/filter/sort. No new pagination or search provider. |
| F17–F22 | DOM verifies drafts and actual save request shape; Python note/history coverage retained. Theme keeps the same editor DOM and selected paper. |
| F23–F32 | Annotation handlers remain unchanged; draft content checked in DOM; existing Python import/provenance/revision tests pass. Full browser import/review/conflict walkthrough remains pending. |
| F33–F43 | Filter/traversal/export logic retained; SVG semantics/escaping/layout tests pass; DOM checks keyboard selection and viewport preservation. Real pointer pan/zoom and rendered graph contrast remain review gates. |
| F44–F48 | Existing clusters/jobs/loading/error/retry and compatibility behavior retained; navigation smoke reaches both sections. No real scheduled jobs invoked by DOM tests; all API responses are synthetic. |

## Required visual review before considering design accepted

Use a disposable synthetic library and a browser with its sandbox enabled. Review all five sections at 1440×900 and 390×844, plus 320px reflow and 200% zoom, in **EN/light, EN/dark, UK/light, UK/dark**. Capture screenshots after rendering; do not reuse the concept or historical images as evidence.

- Check long Ukrainian labels, long publication titles, alert messages, field labels and all graph controls for clipping/overlap.
- Tab from skip-link through navigation, language, appearance, refresh and content; verify unobscured focus and native select behavior.
- Edit notes and an annotation, switch theme, switch locale, navigate away/back and refresh: verify expected draft preservation.
- Follow F01–F48 for remaining pointer, import, errors and export checks. Verify SVG exported independently from each theme.

Chromium was not run with `--no-sandbox`; no host socket, privileged mount or personal dataset was used. Docker workflows and GitHub CI status are not newly certified by this frontend work. GitHub PR-list API returned Forbidden; advertised Git branches showed main and the prior audit/research branches, with no parallel shell implementation.

## Remaining design issues / Phase 2 proposals

- Validate stacked library/detail browsing on phones; consider an explicit return-to-results control only after task testing.
- Evaluate full abstract reading versus the retained nested scroll region, and library/detail width and density with long real-world-shaped synthetic records.
- Test provenance grouping and collapsible secondary controls without losing import, history or conflict feedback.
- Improve graph label legibility at actual screen sizes and offer an accessible relationship-list emphasis on narrow screens.
- Conduct EN/UK task-based usability and screen-reader sessions; public competitor pages and palette arithmetic cannot establish task performance.

These are proposals, not extra features shipped in Phase 1.
