# Gate 3 increment — provider failures and log location

Baseline main `4e2486d3` (merged #27 plus owner `.gitignore` update). Version remains 0.8.0. This focused increment will:

- Replace raw provider exception text in progress messages, search summaries and persisted scan errors with fixed actionable HTTP/network diagnostics, retaining retry behavior and partial success.
- Prove, with disposable data and fake providers, that failed searches retain existing manual library/evidence state and local web read/edit/export/reopen workflows remain usable.
- Standardize all new application file logging on `WORKSPACE_ROOT/log/` across CLI, web, TUI and Telegram; ignore the directory and rotated logs. Adapt the new Telegram file logger, preserve existing legacy scheduled-job paths, and record the rule in AGENTS.

Draft opens before delegation. Implementation and executed validation are pending. No live provider requests, credentials, personal databases, major features, merge, version bump or release. Scheduler disable/remove remains separate Gate 3 work.
