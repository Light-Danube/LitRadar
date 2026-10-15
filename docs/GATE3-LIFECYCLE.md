# Gate 3 lifecycle closure increment

Baseline main `20225a8e` (merged #28). Version stays 0.8.0. Scope:

- Investigate the user's delayed Telegram Ctrl+C shutdown, reproduce with a disposable/fake transport or local server, and fix the smallest confirmed cause while preserving offsets, no-overwrite/data safety and graceful retry behavior.
- Verify scheduler install/status/remove/disable and duplicate-task behavior with synthetic configuration and an isolated Windows harness; identify and fix actual lifecycle blockers. No personal scheduled tasks or live Telegram credentials.
- Independently review closure evidence and run actual Windows/package candidate checks before closing Gate 3. Keep all new/extended file logging under ignored workspace `log/`; generated logs must not be committed.

Draft opens before delegation. Results and closure are pending. No major features, merge, version bump, tag/release, personal database or real-token access.
