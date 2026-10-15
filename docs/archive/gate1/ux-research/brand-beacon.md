# LitBeacon — Beacon Blue visual refinement

Date: 2026-10-14. Branch: `codex/web-brand-beacon`, based on `main` at `a9152bb1`.

## Reference and icon

The user supplied the Telegram mascot as the visual reference: a friendly reader robot, book, lighthouse/beacon, deep blue outlines, cyan eyes, ivory shell and golden light. The colors below are design choices derived visually from that reference, not a claim of exact pixel sampling from the Telegram source.

A new transparent PNG was generated with the image-generation tool and visually inspected as an image. It simplifies the composition to the robot head, open book and antenna lamp, without the wordmark or landscape. The original Telegram asset is not replaced. The new mark is used locally in the web sidebar and favicon; the image is decorative inside the already labelled home link. The wordmark retains readable HTML text in both interface languages.

<img src="../../../../web/static/brand/litbeacon-mark.png" width="160" alt="Generated LitBeacon reader robot with a book and golden beacon lamp">

## Palette and roles

| Reference color | Hex | UI role |
| --- | --- | --- |
| Deep navy | `#071D49` | Identity outline; dark foreground on primary blue controls |
| Ocean blue | `#1458A8` | Light-theme primary action and navigation accent |
| Cyan light | `#42D9EE` | Icon identity; brighter related cyan for dark focus/seed cues |
| Beacon gold | `#FFD45A` | Icon lamp, dark wordmark accent and warning/related-edge text |
| Ivory | `#F6F4EB` | Icon shell and book pages; not a low-contrast body-text accent |

| Semantic role | Light | Dark |
| --- | --- | --- |
| Canvas | `#F4F7FC` | `#07172F` |
| Surface | `#FFFFFF` | `#0E2343` |
| Secondary/hover surface | `#E9F1FC` | `#17385F` |
| Text | `#132743` | `#EEF4FF` |
| Secondary text | `#506079` | `#B8C9E0` |
| Primary accent | `#1458A8` | `#8ACBFF` |
| Focus | `#165EAC` | `#63E0EF` |
| Wordmark gold | `#85600C` | `#FFD45A` |

Gold is darkened in the light theme so the “Lit” text and navigation indicator remain legible. Body text and main reading surfaces retain the Quiet Research structure. No decorative rays, new animation, external fonts, CDN or new production framework were added. On-screen graph colors inherit the semantic tokens; existing self-contained SVG export colors and data semantics remain unchanged.

## Verification

- Python 3.12: **147 passed, 0 failed, 0 skipped**.
- Node: **11 passed, 0 failed, 0 skipped**. Contrast checks now include the wordmark accent as well as text, secondary text, controls and focus. DOM regressions cover theme/locale/drafts/navigation/keyboard/graph state.
- Restricted Python 3.11 container: **142 passed, 0 failed, 5 skipped**. Expected skips: four optional Textual checks and one optional Node XML-export check.
- The asset is served by the existing FastAPI static route. Package data explicitly includes `static/brand/*.png`; a locally built wheel was inspected for the mark.
- Secure Chromium launch still fails at its SUID sandbox helper. The generated PNG was inspected, but no new application screenshot, desktop/mobile rendering, 200% zoom or browser accessibility pass is claimed.

Container verification used the existing locally built `litbeacon:isolated-dev` dependency image and a temporary source-only layer, built with `--network none`, then the actual restricted Compose configuration with an image override. No host binds, network, privileged mode or security relaxation was added. This is not a fresh online Docker dependency build or observation of the remote Actions run.

## Isolated-runner regression fixed alongside this refinement

The new draft-workflow tests had written an executable fake `gh` into `/tmp`. That directory is deliberately mounted `noexec` in isolated Compose. All three cases failed locally in the restricted container before the fix, because the fake command could not run and its call log was absent.

The fake is now a Bash function interpreted by the installed Bash executable. No temporary executable is created; all assertions about PR creation, duplicates, API-list failure and treating branch metacharacters as data remain active. Docker's `noexec`, network restriction and other security settings are unchanged. Remote failure logs are still unavailable through the GitHub API, so this confirms the locally reproduced defect rather than assigning every possible remote failure to it.

## Remaining design review

Review the actual app at 1440px and 390px in EN/UK and light/dark themes. Check the 56px mark in the compact sidebar, the favicon at browser-tab size, long Ukrainian labels, focus visibility, alert contrast and graph selection. If the raster favicon loses detail at 16px, produce a separate simplified beacon symbol in the next design pass. Library/detail navigation, abstract scrolling and provenance grouping remain the Phase 2 proposals from [Phase 1](phase-1.md).
