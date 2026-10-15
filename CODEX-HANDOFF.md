# Codex handoff — local-only LitBeacon 1.0

- Current branch: `codex/gate2-packaged-recovery`, main baseline `0052e202` (merged #25). [Draft PR #26](https://github.com/Light-Danube/LitRadar/pull/26) was opened before delegating archive and package-smoke work.
- Gate 1 is complete. Its dated plans, validation records and previous handoff are in the [archive index](docs/archive/gate1/README.md); keep active setup/user/recovery guides discoverable. Historical proposals and pending claims are not current instructions.
- This PR only archives completed records and extends installed-wheel smoke with synthetic backup/restore: all durable rows, histories/tombstones, elected artifacts/checksums, integrity and no overwrite. Runtime recovery logic is unchanged. See [active checklist](docs/LOCAL-1.0-RELEASE-CHECKLIST.md) for candidate test/CI evidence.
- Continue vertically: finish Gate 2 package evidence before Gate 3. Gate 3 has two unchecked items. The smallest next fix is optional Telegram polling conflict handling: `telegram_bot.py` recognizes HTTP 409 but `run_forever` retries every exception indefinitely. Add a specific conflict error and safe nonzero exit with fake-API regression tests; preserve transient retries and local/offline workflows. Do not expand this PR.
- User-reported Windows daily-use/Narrator acceptance is recorded; Narrator is optional. Cloud live-venue proxy 403 remains an environment limit, separate from the user's successful CLI use.
- Version remains **0.8.0**. No merge, version bump, tag/release, major new feature, personal database, credentials or model-cache access. Use only disposable synthetic fixtures. Follow [AGENTS](AGENTS.md) and [ROADMAP](ROADMAP.md).

Executed local candidate checks: **518 Python / 38 JS passed, 0 failed, 0 skipped**; fresh extracted setup-wheel Linux recovery/web smoke passed. One existing Starlette warning. Candidate Ubuntu/Windows CI is pending; see active checklist for commands and limits.
