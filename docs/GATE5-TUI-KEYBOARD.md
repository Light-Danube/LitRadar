# Gate 5 — EN/UK TUI modal keyboard checks

Next small slice after merged PR #34, baseline main `cf3f0a86`. Scope: existing Textual Help, tag editor and Jobs modal keyboard navigation, scroll/close/cancel/focus restoration and persistent errors, in English and Ukrainian with disposable data and mocked external operations. Fix only a reproduced defect. No new TUI design or general accessibility certification.

## Reproduction and bounded fixes

- The initial six Help/tag/Jobs EN/UK keyboard checks passed after correcting a test-only profile-default fixture. Two added tag-save error cases produced **6 passed / 2 failed**: a synthetic SQLite failure escaped the input handler and stopped the app. Enter and Save now share one guarded save path. Failure rolls back a pending write, retains input/focus and displays a fixed localized persistent retry/cancel message without exposing raw exception content.
- Long Jobs diagnostics could not receive keyboard focus; making the old Static widget focusable alone also failed full-content scrolling. The existing status text now sits inside a standard focusable `VerticalScroll`, retaining existing Static updates. Tab/Shift+Tab reaches the output; Home/End and the standard scroll keys navigate it. A visible focus cue marks the pane. No scheduler behavior or task registration changes.

## Executed local evidence — 2026-10-17

- `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra tests/test_tui_keyboard_locales.py`: **8 passed, zero failed/skipped**, Linux Python 3.12.14, Textual 1.0.0. Fresh lightweight dev/UI/web/annotation dependencies were installed into ignored scratch space; no semantic/model packages or weights.
- Help checks use real Pilot keyboard events at 80×24: translated content/buttons, End scrolling, Tab/Enter close and Escape, focus return, retained query and blocked underlying status/feedback/source-search shortcuts.
- Tag checks exercise Unicode typing, save/cancel, localized controls, preserved filters/query and focus return. Injected writes followed by SQLite errors leave no pending transaction; old tags survive failure, retry succeeds, and a later failed Save can be cancelled without committing the draft.
- Jobs commands are mocked. Localized error wrappers persist, controls recover, selected temporary config/profile paths are used, and no OS task is touched. A 50-line result is keyboard reachable, scrolls to the full maximum with End and back to zero with Home, then Escape returns focus to the library.
- Full `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra`: **740 passed, zero failed/skipped**, Linux Python 3.12.14; one existing Starlette warning. `npm ci --prefix tests/web --ignore-scripts` (scratch cache), then `npm test --prefix tests/web`: **44 passed, zero failed/skipped**. No JavaScript changed.
- Changed Python syntax, **105 local documentation targets/anchors**, whitespace and no-tracked-logs checks passed. Version/package metadata, backend/schema, ranking, web assets and dependency lockfile are unchanged. Generated output is ignored.
- No native Windows, terminal rendering, Narrator speech, participant study or accessibility certification is inferred. Literal subprocess output remains untranslated; only the UI wrappers are localized. Tests use disposable data and mocked external operations, not real providers or models. A separate subagent reviewed the combined fixes and limits.

## Remaining work and limits

Gate 5 remains open for remaining web/Research keyboard and ordinary-user venue lookup/evidence save/export evidence. Existing user-reported Windows/Narrator acceptance stays separate; Narrator remains optional. The next small slice is that existing browser Research workflow, not a new UI design or broader TUI overhaul.

Hosted Actions remain deferred by user instruction because billing prevents jobs starting; no retries/monitoring or new Windows/CI pass. New/extended file logging remains under ignored shared `log/`; scratch test output and logs are not committed. Version stays 0.8.0; no personal database, `.env`, credentials/model-cache access, major feature, merge, version bump, tag or release. Backend/schema and scheduler lifecycle remain unchanged.
