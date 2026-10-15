# Textual TUI accessibility and workflow audit

Historical audit: 2026-10-14. Scope: existing LitBeacon Textual TUI only. On **2026-10-15 the user confirmed Windows daily use and Narrator work okay and accepted them as “yes”**. This is user-reported acceptance; exact platform/reader versions and per-task observations were not supplied. Narrator is optional for this release. The broader detailed assistive-technology procedure below remains optional and incomplete; no formal certification is claimed.

## Executed evidence

Environment: Linux, Python 3.12.14, Textual 1.0.0. Tests use Textual's real `App.run_test` lifecycle and Pilot keyboard events with disposable SQLite databases and two synthetic papers. Scheduler subprocesses, online providers and citation lookups are mocked; no actual scheduled tasks, network requests, downloads or personal research data are used.

` .venv/bin/python -m pytest -q tests/test_ui_workflows.py --tb=short `: **19 passed in 13.66s**. This run used the execution environment outside its restricted sandbox after restricted runs hung during event-loop teardown. The same tests, including native Textual notifications, pass there. The restricted-run hang is not evidence of an application defect.

| Area | Executed check | Result and limit |
| --- | --- | --- |
| Status workflow | Real `t`, `r`, `d`, `u` keys; durable SQLite status | Pass |
| Feedback | Real `y`, `n` keys; feedback persisted | Pass; notification speech not tested |
| Library filters | Title sort, status, tag, search with no results | Pass; zero selection actions do not mutate papers |
| Detail text | Synthetic abstract containing `[literal]` | Pass; literal text preserved |
| Tags | Initial input focus, literal shortcut letters typed, Enter save, Escape cancel | Pass; app shortcuts do not interfere with typing |
| New tag filter | Newly saved tag immediately selected in main filter | Pass; regression for stale tag options |
| Help modal | Workflow keys and Ctrl+Enter while help is open | Pass; underlying paper/provider workflow remains inactive |
| Help navigation | Keyboard End scroll at 80×24; close and return to paper-table focus at 80×24/120×40 | Pass |
| Scheduled jobs | Initial status plus refresh, install scan/digest, remove scan/digest/all via keyboard | Pass with mocked scheduler |
| Scheduler failures | OSError, timeout, nonzero exit and empty output | Pass; visible result and controls enabled again |
| Scheduler lifecycle | Controls disabled while running, second command rejected, Escape during active worker, late result | Pass; dialog closes without app crash |
| Online search | Synthetic success with durable progress 100%; provider exception | Pass; fetch control recovers |
| Citation exploration | Synthetic provider exception | Pass; busy state and fetch control recover |
| Offline save | Mocked PDF/metadata success and OSError from storage | Pass; failure remains in the activity panel and app stays alive |
| Open destinations | Local-PDF preference and DOI URL with intercepted browser calls | Pass; no external destination opened |

Localization has separate EN/UK catalog and Pilot tests. Their final counts belong in the patch's validation report; they are not included in the 19 workflow tests above.

Final combined checks: **430 Python passed / 0 failed / 0 skipped**, **6 Node test files passed / 0 failed / 0 skipped**. TUI subset: **29 passed / 0 failed / 0 skipped**. A native ANSI PTY smoke at 80×24 also completed with Ukrainian synthetic content and mocked jobs; it verifies terminal execution, not spoken output or visual usability. The disposable audit fixture's `--smoke` check passed separately. Python reports one existing Starlette TestClient deprecation warning.

Historical [PR #19](https://github.com/Light-Danube/LitRadar/pull/19) is merged. Its early head `85d841dc` had `action_required` with no jobs; this was not a test failure. Current executed CI is tracked in the [release checklist](LOCAL-1.0-RELEASE-CHECKLIST.md); historical pending status is not a current blocker.

The implementation now requires **Textual >=1.0,<2**, consistently in `requirements-ui.txt` and the package UI extra. Testing the old declared minimum 0.50.1 exposed incompatible binding APIs; new runtime localization and focus APIs are supported and tested on 1.0.0. Upgrade UI dependencies before running this patch. No application release-version bump is made.

## Ukrainian interface

Use the English/Українська selector next to online search. Switching preserves both query fields, filters and the selected paper. Set `LITBEACON_TUI_LANGUAGE=uk` for Ukrainian at startup (legacy `LITRADAR_TUI_LANGUAGE` is also accepted); otherwise the default is English. The selector changes this session only. App labels, help, statuses, sorting, job buttons, notifications and known pipeline summaries are localized. Paper data, provider/CLI diagnostic output and technical identifiers stay literal. Framework-owned command-palette/theme dialogs may retain Textual's English strings.

## Defects and changes

The jobs crash originated in `ScheduleScreen._run_schedule`: `Screen` has no `call_from_thread`, so the scheduler worker raised `AttributeError`, and Textual's default worker error handling terminated the app. Results now dispatch through the owning App. Busy controls prevent overlapping scheduler mutations; cancellation and mounted-screen guards prevent late UI updates after closing the dialog. Scheduler error messages are retained in the dialog.

Saving tags previously refreshed paper rows without rebuilding the tag selector. The close callback now refreshes tag options before rows, so a new tag is immediately usable as a filter.

Offline saving could also terminate the app when storage raised an exception (for example, a full disk). The worker now reports a localized persistent error and keeps the app alive. Closing Jobs stops its UI updates; it does not roll back or guarantee cancellation of a command already sent to the OS scheduler.

Help, details and jobs now have keyboard-focusable scrolling regions. Help has an explicit Close button; jobs initially focuses Close. Focus borders add a shape cue alongside color. Jobs buttons use separate full-width rows so long Ukrainian labels can be reached through keyboard scrolling. These are code and Pilot findings, not screen-reader or human usability certification.

## Assistive technology and visual gates

Ordinary shell commands report `TERM=dumb`, no stdin/stdout TTY, and no `DISPLAY` or `WAYLAND_DISPLAY`; the executor can separately allocate an ANSI PTY, used for the smoke above. `orca`, `brltty`, `speech-dispatcher`, `espeak`, `espeak-ng`, `speakup`, and `pwsh` are not installed. No supported desktop terminal/screen-reader session is attached. Installing a speech synthesizer alone would not establish an accessible terminal or verify speech and Braille output. No real assistive-technology pass is claimed. The user selected **Windows Terminal + Narrator** as the primary audit environment.

| Remaining gate | Required environment and procedure | Acceptance evidence |
| --- | --- | --- |
| Windows speech (primary) | Narrator with Windows Terminal; run EN and UK | Record exact Windows, terminal, Narrator, Textual versions; input/filter names, row selection, details and dialog focus are understandable; UI updates and errors can be reviewed |
| Other readers (additional coverage) | NVDA with a supported Windows terminal | Same tasks; report separately from Narrator |
| macOS speech | VoiceOver with Terminal; EN and UK | Same tasks; record interaction mode, reading order, selection updates and return focus |
| Linux speech | Orca with a supported accessible terminal such as GNOME Terminal; EN and UK | Verify actual terminal accessibility support and readable output; record any terminal-specific limitations |
| Braille | Actual display or documented screen-reader Braille viewer | Titles, status, Unicode Ukrainian, focus and modal content can be reviewed without relying on speech |
| Visual contrast | Actual terminal default/light/dark/high-contrast palettes | Measure rendered foreground/background pairs, including focus, muted status and search highlights; target 4.5:1 text and 3:1 relevant UI cues; code colors alone cannot prove this |
| Reduced size/magnification | Real terminal at 80×24 and smaller, enlarged font, EN/UK | All existing actions reachable; labels and paper details recoverable through scrolling; no destructive action invoked by clipped labels |
| Participant keyboard review | User operating an actual terminal without a mouse | Discoverable shortcuts, predictable Tab/Shift+Tab, modal escape and focus restoration; record issues and task outcomes |

For each reader session, use a disposable database with a long Ukrainian title, a long abstract, two statuses and two tags. Complete filtering, sort, status change, feedback, tag save/cancel, help scroll/close and mocked jobs success/failure. Review provider progress without a live request. Verify that `q`, workflow letters and Ctrl+Enter do not invoke the underlying app while a modal is open. Verify that notifications and persistent error/progress text can be read without visual inference. Tooltips and visible text do not constitute a proven accessible name in a terminal; record what the reader actually announces.

## Remaining product findings

Below 110 columns the toolbar now uses two rows; the online input has a flexible width so Fetch and the language selector remain visible. Jobs and help scroll on short terminals. These targeted fixes do not implement the full menu draft: the footer still has more shortcuts than fit on one line, table/details remain side by side, and very small terminals still need the proposed pane switch/stacked controls. Persistent progress is preferable to a disappearing toast for critical state, but notification speech behavior requires the reader sessions above.

## Windows Terminal + Narrator procedure

Run from the repository in Windows Terminal after installing `python -m pip install -r requirements-ui.txt`. Use the prepared fixture rather than a personal library:

```powershell
python scripts/tui_accessibility_fixture.py --language uk
```

The fixture uses a temporary database with two synthetic papers. All scheduler, provider, offline download and browser actions are simulated; configuration loading is replaced so no `.env` or personal research profile is read. Changes disappear when the session ends. `Remove all` simulates a scheduler failure; online query `error` simulates a provider failure. Other source/job actions simulate success.

1. Start Narrator with Windows+Ctrl+Enter. Record Windows/Windows Terminal/Python/Textual versions, Narrator voice/language, terminal font/size, and whether Narrator scan mode is enabled. Use the Narrator key+Space to toggle scan mode if it intercepts app keys; record the mode that works. Use an English keyboard layout for the existing Latin shortcuts and enter Ukrainian text in fields separately.
2. At 120×40 then 80×24, Tab/Shift+Tab through local search, status/sort/tag filters, online search, Fetch, language, table and details. Record the **actual spoken names and values**, not just visible text. Confirm search text entry does not mark papers or close the app.
3. Select each paper using arrows; read its full title, status and long abstract. Focus details and scroll. Verify the reader can distinguish selection from other rows and revisit content after a redraw. If terminal output cannot be read reliably, record a failed gate and the precise obstacle.
4. Use T/R/D/U and Y/N with focus on the table; verify status and feedback can be reviewed. Open G, type `тестовий, review`, save with Enter, cancel a second edit with Escape, and select the new tag in the filter. Confirm return focus and unchanged underlying data on cancel.
5. Open `?`, scroll the help with End/PageDown, Tab to Close, close, and check focus returns. Open J; read the platform caveat and synthetic status, activate each job control, then Remove all. Review the persistent error text and close via Escape. No actual Windows tasks are changed.
6. Fetch a normal query, then `error`; review progress, completion and failure. Test Ctrl+Enter while help/jobs is open: the underlying source search must stay inactive. Confirm that updates do not move focus and errors remain available after any toast disappears.
7. Repeat with `--language en`, enlarged terminal font, and the Windows Terminal high-contrast settings actually used. Record EN/UK pronunciation, any lost focus/output, colors/shape cues and a usable reading path. Quit via Ctrl+Q or Q outside text fields.

Record one row per task: `environment | language/size | task | spoken output | pass/fail | obstacle | workaround`. A successful fixture launch is not a Narrator pass. Attach concrete results before checking the full roadmap audit item; any inaccessible task remains an open defect.

The roadmap records user-reported Narrator acceptance and its optional release status separately from these automated tests. A detailed cross-reader audit remains incomplete; do not turn this acceptance into invented speech/Braille/contrast observations or certification.
