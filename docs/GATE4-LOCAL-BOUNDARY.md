# Gate 4 — local web launch boundary

Small first slice of Gate 4, based on main `bc9cbde7` (merged PR #29). Version remains 0.8.0. Scope: the existing CLI's loopback-only web launch, its source launcher and the documented Docker host-port boundary. Path/upload/export and SQLite integrity checks remain separate Gate 4 work.

## Verification plan

- Verify default/explicit loopback CLI launch and rejection of non-loopback bind arguments before creating an application or opening a database/browser.
- Start a real web listener with a disposable library, inspect its bound socket, request local health and stop it cleanly. No personal database or live provider request.
- Check source launcher forwarding and distinguish container-internal binding from Compose's host-loopback publication.

Executed results will be recorded after local verification. GitHub-hosted Actions are deferred at the user's request because account billing prevents jobs starting; failed/canceled startup checks are not application test results. No workflow disabling, billing changes or CI pass claim.
