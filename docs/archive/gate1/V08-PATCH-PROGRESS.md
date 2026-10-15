# v0.8.x patch progress and remaining 0.8.5 gates

Branch: `codex/v08-semantic-graph-workflows`, base main `54f48330`.

## Implemented

- OFF-default local semantic workspace flag and optional dependency; ephemeral undirected related edges can participate in bounded seeded traversal. Complete-link embedding clusters remain separate from heuristic grouping. Current metadata is refreshed on cache hits and computed edges never enter the citation table.
- Bounded deterministic collision settling reserves circle/label footprints. A dragged node is pinned while conflicting nodes are repositioned on release; this is a short settling pass, not an animated force engine. Layout/export data remain coherent.
- Ordinary node selection retains its pointer capture on the node, so a stationary click is not retargeted to the SVG. Dragging suppresses accidental selection; Enter/Space and Shift+arrows remain.
- SVG/GraphML/JSON exports are grouped in a native details menu with Escape/focus handling. Zoom buttons remain for keyboard users alongside wheel zoom.
- Mixed OpenAlex/Semantic Scholar fixtures exercise identifiers, direction, self/duplicate suppression, antiparallel citations, cycles, cache refresh and merged provenance. EN/UK DOM and API workflows cover inbox editing, clusters and graph/detail navigation.
- Windows CI runs these workflows plus a native Chrome script on synthetic data, with sandbox enabled, blocked external browser requests and unique repository-local DB/profile directories. Screenshot artifacts are restricted to this run's PNGs.
- AGENTS.md now documents architecture, feature flags, data/recovery contracts, isolation, collaboration, verification and release rules.

## Evidence

- Python 3.12: **186 passed, 0 failed, 0 skipped**.
- Node: **28 passed, 0 failed, 0 skipped**.
- Restricted Python 3.11 Docker: **179 passed, 0 failed, 7 expected skips** (Textual 4, Node 1, optional PDF/BibTeX 2). Source-only offline layer over the existing dependency image; no fresh online build is claimed.
- A six-title attributed public corpus and evaluation CLI are available. Executed lexical control: recall 0/3 at .72; at .5 precision 1/1, recall 1/3. These are not neural-model quality results. Crossref/Hugging Face metadata requests returned proxy 403.
- Native Windows Chrome script is syntax-checked and configured to run through the workflow, not run here. The cloud browser sandbox limitation remains; user baseline visual acceptance does not turn this into a new browser result.

## Version remains unchanged

The requested **0.8.5** bump is conditional on completion of the requested gates. Two remain unconfirmed:

1. An actual successful Windows/native-Chrome workflow result.
2. Quality evaluation with a real local neural model on the shareable corpus (and verification/expansion of its manually curated metadata as appropriate).

No version was bumped to imply these are complete. Current runtime/release metadata remains 0.8.0; the changes are unreleased. The existing redesign checklist is accepted on the user's instruction, without inventing third-party participant or hands-on competitor results.

Next agents should inspect [Windows instructions](../../WINDOWS-WORKSPACE-SMOKE.md) and [semantic evaluation](../../SEMANTIC-WORKSPACE.md), obtain actual outcomes, and then apply the authorized version bump consistently across VERSION, package/FastAPI/web/CLI/TUI/Telegram current labels, packaging tests and current-release docs. Historical changelog versions and legacy identifiers remain historical/compatible.
