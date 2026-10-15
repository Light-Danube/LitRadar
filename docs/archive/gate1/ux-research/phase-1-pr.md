# Quiet Research Phase 1: responsive shell and persistent light/dark themes

The browser workspace previously had a single dark palette, fragmented component colors and cramped shell controls on narrow screens. This change introduces shared semantic tokens, a responsive shell and localized System/Light/Dark appearance selection. Changing appearance preserves the current editor DOM, unsaved notes/annotations and graph selection/viewport.

The five existing sections and the 48 documented feature contracts remain in place. Production stays HTML/CSS/vanilla JavaScript with no new build system, backend endpoint, database migration or deployment change. Standalone SVG exports retain their self-contained dark fallback colors.

Validation:

- Python 3.12: 144 passed, 0 failed, 0 skipped.
- JavaScript: 11 passed, 0 failed, 0 skipped; locked, test-only jsdom regressions cover preferences/storage, EN/UK, drafts, shortcuts, save payload and graph state. Graph/export and palette contrast checks are included.
- All four shipped JavaScript files pass syntax checks; diff whitespace check passes.
- Secure Chromium failed before rendering because the environment's sandbox helper is not configured. No new browser screenshots or visual acceptance claim; desktop/narrow-screen, EN/UK and light/dark visual review remains required.
- Current GitHub CI status and the complete open-PR list could not be inspected because the API returned Forbidden. No permissions or credentials were changed.

[Implementation, parity evidence and visual checklist](phase-1.md) · [Current public competitor review](live-review-2026-10-13.md)

Phase 2 proposals: validate mobile library/detail browsing and abstract scrolling, provenance grouping, graph readability and task-based EN/UK usability. These proposals are not implemented here.

Target: `main`. Head: `codex/web-redesign-shell`. Create as a **draft**; do not merge automatically.
