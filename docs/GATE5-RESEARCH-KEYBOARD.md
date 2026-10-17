# Gate 5 — Research browser keyboard journey

This small PR checks the existing English/Ukrainian Research flow from the sidebar through venue choice, evidence editing and saved comparison download. It follows merged PR #35 on `main` (`be81f40a`). The check uses synthetic responses and disposable page state; no live scholarly request or personal library is involved.

The current DOM suite reaches those actions by direct clicks and form submission. This slice adds keyboard focus/activation assertions at the transitions where new results, a worksheet or a saved download appear, and fixes only reproduced focus gaps. It will record executed checks and remaining native-browser/user limits before review. Gate 5 and release approval stay open until their evidence is assessed.
