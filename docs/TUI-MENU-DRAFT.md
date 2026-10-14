# LitBeacon TUI menu draft

Status: design proposal, 2026-10-14. This document proposes a follow-up arrangement of existing Textual controls. It does not implement a new menu or claim terminal rendering or assistive-technology validation. The localization and crash fixes can ship independently of this proposal.

## Scope and observed problems

The source baseline is `ui.py` / `ui.tcss`, inspected before the current localization changes. Preserve the saved-library workflow, existing provider search, selected-paper actions and scheduled-job manager. Keep existing backend behavior, stored identifiers and shortcuts. No CLI-only or web-only features are proposed: no venue-discovery form, annotation editor/history, embedding controls, new graph viewer, or export workflows.

The current toolbar reserves approximately 94 columns for status, sort, tag, counts, spacing and padding before giving any width to the local-search input. This cannot fit an 80-column terminal. The main pane permanently divides the remaining space 2:1 between table and details. The idle progress panel consumes five rows. The footer exposes 19 bindings at once, while most selected-paper actions have no visible button/menu entry. Help omits the existing `K` tag-filter and `I` DOI bindings. Jobs uses long installation labels and four horizontal removal/close buttons. These are source observations; they are not results from a native-terminal study.

The accompanying bugfix patch addresses the initial help omissions, keyboard scrolling, stacked Jobs buttons, flexible online input and a two-row toolbar below 110 columns. The complete menu proposal below remains a draft: no grouped paper-action menu or compact pane switch is implemented. The primary user-selected reader for follow-up is Windows Terminal + Narrator; see [the executed audit and its fixture](TUI-ACCESSIBILITY-AUDIT.md).

## Proposed arrangement

Use one stable library screen with three clearly named control groups:

| Group | English / Ukrainian | Existing controls |
| --- | --- | --- |
| Library | Library / Бібліотека | Local search, status, sort, tag, library/view counts |
| Discovery | Online search / Пошук онлайн | Source query, Fetch papers, persistent activity/progress |
| Selected paper | Paper actions / Дії зі статтею | Reading status, feedback, tags, offline save, open, DOI, bounded citation exploration |

Keep `Jobs / Завдання`, `Help / Довідка`, language selection, and quit in a small global strip. Put selected-paper actions in one ordinary focusable button opening a grouped action list. A list item invokes the existing action method; it does not duplicate its logic. Show the selected paper title or ID in the menu and disable paper actions when no paper is selected. Preserve all direct shortcuts. Opening the menu adds a discoverable route for users who cannot remember shortcuts.

Suggested wide-terminal wireframe (labels are schematic; widths must be verified):

```text
LitBeacon                    English/Українська  Jobs J  Help ?
Library: [local query____________________]   Library: 120 / View: 12
Status: [All_______]  Sort: [Relevance____]  Tag: [All tags______]
Online search: [provider query_________________] [Fetch Ctrl+Enter]
Activity: Ready.                     [expand existing activity]
┌ Papers ─────────────────────────────┬ Details ──────────────────┐
│ ID  Score  Status  Year  Title       │ Selected title            │
│ ...                                 │ metadata and abstract      │
│                                     │ [Paper actions]            │
└─────────────────────────────────────┴───────────────────────────┘
/ Search     Paper actions     J Jobs     ? Help     Q Quit
```

An activity expander only changes presentation of the already-existing progress and messages. The final summary and any error stay visible when compact; expansion reveals provider lines without losing them. Do not move focus or auto-scroll the library when background events arrive.

## Responsive behavior

Provisional layout thresholds should be measured with both translations:

| Terminal | Proposed behavior |
| --- | --- |
| At least 110 columns and 30 rows | Table/details side by side; filters on their own row; full activity while a task runs |
| 80–109 columns | Local search and counts on separate lines if needed; filters wrap into two rows; table and details share a focusable view switch; selected row survives switching |
| 60–79 columns or fewer than 24 rows | One pane; controls stack in a vertically scrollable container; activity defaults to a one-line summary with an explicit expand control |
| Below 60 columns | State the supported minimum and offer a scrollable compact view; keep close/help/quit reachable rather than silently clipping controls |

The view switch reorganizes existing details, not paper data. Keep title and status visible in the compact table; optional ID/score/year columns can move into existing details. Long titles may truncate visually, but the complete title remains available in details. Filters, open menus and selected paper survive resizing. Modal width must be bounded by viewport width with small margins; long content and action lists scroll vertically. No essential button should require horizontal scrolling.

## Preservation map

| Current action / binding | Proposed discoverable location |
| --- | --- |
| Select row, arrows, Enter | Papers table; selection opens existing details |
| Local search `/` | Library search field |
| Status `F`, sort `S`, tag filter `K` | Labeled library filters; all current sort choices, including Personalized, remain |
| Source query and Fetch `Ctrl+Enter` | Online search group; preserves distinct local and remote query fields |
| To Read `T`, Read `R`, Dismiss `D`, Restore `U` | Paper actions → Reading status |
| Useful `Y`, Not relevant `N` | Paper actions → Feedback |
| Edit tags `G` | Paper actions → Tags; current save/cancel dialog |
| Offline save `L` | Paper actions → Save offline |
| Open PDF/URL `O`, open DOI `I` | Paper actions → Open; maintain current local-file/URL preference |
| Citation exploration `C` | Paper actions → Explore citations; same existing bounded ingestion and activity output |
| Scheduled jobs `J` | Global Jobs control; same scan/digest defaults and platform caveats |
| Help `?`, Quit `Q` | Global controls and compact footer; complete reference in Help |

Group the Jobs dialog by job, rather than by operation: `Scan / Сканування` with its existing install/remove actions, then `Digest / Дайджест` with its existing install/remove actions. Keep `Refresh status`, `Remove all`, and `Close` below, stacking at narrow widths. Show the exact daily/weekly times beside installation actions. Retain the Linux/macOS cron/launchd caveat and the distinction between removing jobs and deleting papers. Preserve the existing defaults; this draft does not add schedule editing.

## Keyboard, focus and localization contract

Give every field a persistent label; placeholders only provide examples. Keep `/`, `F`, `S`, `K`, and existing paper-action bindings active outside editable fields. Typing their letters in inputs must insert text. Keep Latin shortcuts stable in both languages and display them next to translated menu labels; do not assume Ukrainian keyboard layout produces Latin key events. Explicitly test both physical layouts before deciding whether alternate bindings are needed.

Tab and Shift+Tab traverse visible controls in screen order: global strip, library query/filters, online query/fetch, activity expansion, table, details/view switch, paper actions, footer controls if focusable. Avoid making duplicated footer shortcuts additional tab stops. Focus stays inside an open modal; Escape cancels and returns to the invoking control. Help and Jobs include focusable Close buttons. Tag save returns to the selected row/action control without resetting filters. A submenu closes before any modal opens. Closing the app is distinct from closing a dialog.

The action menu must be operable with arrows, Enter/Space and Escape. Preserve a strong visible focus marker and a textual selected state under monochrome/high-contrast terminals. Do not convey read/dismissed states, progress, errors, disabled actions or focus with color alone. Provide a focusable, scrollable reading surface for details and persistent task status; progress bars supplement written phase/error/completion messages.

Use the shared EN/UK localization mechanism for all proposed labels, group headings, explanations and disabled reasons. Stable action identifiers and stored statuses remain unchanged. Keep paper titles, abstracts, tags and provider diagnostics as supplied content; translate surrounding labels. Translation switching preserves input drafts, filters, selection and active jobs. Measure Ukrainian labels rather than allocating widths from English strings.

## Acceptance checks before implementing this draft

1. Demonstrate every preservation-map action through both its existing shortcut and its menu/control using synthetic data. Use scheduler/network/browser mocks; ordinary tests must not install real jobs or open external destinations.
2. At 120×40, 100×30, 80×24 and 60×20, inspect both EN/UK: no clipped essential control, reachable modal close/cancel, readable job operations, retained selection and drafts after resize. Below the minimum, verify the explanatory state and exit path.
3. Keyboard-only walk-through: complete local filtering, online query, selected-paper status/feedback/tags/offline/citations, and all Jobs operations. Verify backwards traversal, modal focus return, nested menu dismissal, input shortcut isolation and empty-library behavior.
4. Exercise background success/error/timeout and closing Jobs while status is running. Status updates must never steal focus, update a detached screen or crash the app. Preserve the previous durable error/result until a new operation starts.
5. Run a real terminal with assistive technology: NVDA with the supported Windows terminal, and Orca or a Linux console reader where usable. Record OS, terminal, reader/version, input mode, spoken output, task results and obstacles. Verify focus identity, selected row/title, filter values, text entry, menu groups, progress/error reading and modal exit. Automated Textual pilots do not prove spoken announcements.
6. Test terminal scaling, high contrast/monochrome, Cyrillic entry, long abstracts/tags and unsupported/empty data. Distinguish library bugs from terminal/reader limitations and document a workable reading path where available.

This proposal is ready for review as a separate menu iteration. Native-terminal and assistive-technology evidence remain required before calling the proposed layout accessible or marking a full audit complete.
