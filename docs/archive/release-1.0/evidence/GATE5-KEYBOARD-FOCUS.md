# Gate 5 — annotation edit keyboard focus

First small Gate 5 slice after merged PR #33, baseline main `2130f707`. Scope: opening and canceling the existing supplemental annotation editor in the English/Ukrainian web UI, with focus restoration and preservation of unrelated drafts. Keep automatic draft restoration from stealing focus. Gate 5 remains open for broader web/TUI keyboard, scrolling/error behavior and ordinary-user Research workflow evidence.

## Reproduction and behavior

- The independent six-case EN/UK DOM baseline yielded **4 failed / 2 passed**, zero skips: explicit Edit left focus on the Edit button and Escape inside the editor was unhandled. Draft rehydration already preserved header/other-field focus.
- Explicit Edit now focuses its textarea. Cancel or non-composing Escape from controls inside that editor clears only its edit and returns focus to the corresponding Edit button. Cancel/Escape send no mutation request; they do not undo a Save already submitted. Unrelated paper notes, new-annotation content/provenance and other inline edits stay intact.
- Escape during text composition and Escape outside the inline editor do not cancel it. Reopening a cancelled edit starts with saved content. Automatic restoration across language/navigation changes does not take focus, including delayed annotation loading while another field is focused.

## Local verification — 2026-10-17

Independent regressions run production scripts with fake API responses in jsdom. After the fix, **6 EN/UK cases passed, zero failed/skipped**. They use DOM focus/button activation and dispatched key events; they do **not** establish native Tab/Shift+Tab order, physical Enter/Space activation, rendering, scrolling, Windows Terminal or screen-reader behavior. No real library, provider or model is used.

- Full `PYTHONPATH=/workspace/LitRadar/work/test-deps python -m pytest -q -ra`: **732 passed, zero failed/skipped**, Linux Python 3.12; one existing Starlette warning. This includes existing Textual event-loop checks, not new EN/UK TUI task acceptance.
- `npm ci --prefix tests/web --ignore-scripts` (scratch cache), then `npm test --prefix tests/web`: **44 passed, zero failed/skipped**, including all six new keyboard-focus cases.
- Changed JavaScript syntax, **187 local documentation targets/anchors**, whitespace and no-tracked-logs checks passed. Version/package metadata, schema/backend code and the Node dependency lockfile are unchanged.
- Runtime fix and independent baseline/regression checks used separate subagents; root reviewed the combined result. Canceling unsaved edits is tested; undoing an already submitted Save is not promised.

## Remaining Gate 5 work

The broader web/TUI keyboard, help/modal scrolling, persistent errors and ordinary-user venue lookup/evidence save/export evidence remain open. Existing user-reported Windows/Narrator acceptance stays recorded separately; Narrator is optional and no accessibility certification is claimed. Next small slice: TUI EN/UK modal navigation, cancel/focus return and help scrolling, followed by the remaining Research workflow checks.

Hosted Actions remain deferred by user instruction because billing prevents job startup; no retries/monitoring or new native Windows/CI pass. Application file logging remains under ignored shared `log/`; scratch test output is not committed. Version remains 0.8.0; no personal data, major feature, merge, version bump or release claim.
