# Telegram listener diagnostics

Telegram is optional. Your saved library, web UI and TUI do not require a bot token or a running listener. Scheduled digest delivery runs independently of the listener.

Start one listener per bot token:

```sh
python cli.py telegram-run
```

For a support/debug session, choose an existing writable directory and a separate file for this listener:

```sh
python cli.py telegram-run --debug --log-file telegram-listener.log
```

An installed wheel uses the same commands with `python -m cli`. Console diagnostics are timestamped with the process's local time and UTC offset. Normal logging includes lifecycle, warnings and failures; `--debug` adds safe API method, outcome and elapsed-time records. File logging is opt-in, UTF-8 and append-only between rotations: 1 MiB per file, three older files (`.1`–`.3`). An existing file may contain older content from another program; review it before sharing. Ctrl+C closes the listener and log handles. A logging setup failure returns exit code 2 before starting the listener.

The listener omits tokens, token-bearing URLs, chat/update IDs, request/response bodies, message/research content and raw exceptions from its diagnostics, including DEBUG. Unknown local failures use a fixed message rather than a traceback. Keep the original problem's safe status/method/time when reporting it; do not send `.env`, database files or bot credentials. These logs are operational diagnostics, not an audit trail of every user action.

| Diagnostic | Next step | Listener behavior |
| --- | --- | --- |
| 400 — request rejected | Check bot/chat configuration and request settings locally. | Polling stops; CLI exits 2. |
| 401 — authentication failed | Check the bot token locally; replace it through BotFather if invalid. | Polling stops; CLI exits 2. |
| 403 — access denied | Check permissions, configured chat and whether the bot was blocked. The status alone does not prove which cause applies. | Polling stops; CLI exits 2. |
| 404 — endpoint not found | Check token configuration and installation. | Polling stops; CLI exits 2. |
| 409 — polling conflict | Stop other Windows/container listeners and `telegram-chats` sessions using this token. An existing webhook can also prevent polling; review it manually. | Polling stops; CLI exits 2. No webhook is changed and no process is killed. |
| 429 — rate limited | Wait before retrying; reduce competing requests. | Accepts integer waits of 1–3600 seconds; missing/invalid waits use five seconds. A requested wait above 3600 seconds stops polling with exit 2 and manual-retry guidance. |
| 5xx — service unavailable | Retry later; the saved library remains local. | Polling retries. |
| Timeout, DNS, network/proxy or TLS failure | Check connectivity, proxy, system time and certificate trust. Keep TLS verification enabled. | Polling retries. |
| Invalid JSON/API response | A proxy or service may have returned an unexpected response; check connectivity and installation. | Polling retries. |

A rejected command-menu setup is a warning; commands can still work. A failure while processing one update is reported safely and retains the existing offset/skip behavior, so this change does not add guaranteed command replay or automatic resend. A failed poll does not advance the saved offset. Ctrl+C also stops a retry wait cleanly.

This increment covers `telegram-run` diagnostics and the fixed replies/persisted failure records for caught listener exceptions. Existing provider scan summaries and scheduler subprocess result messages retain their separate behavior. It does not introduce global debug logging, capture HTTP wire traffic, or replace the independent scheduled-digest/`telegram-chats` transports. In particular, their existing diagnostics are not covered by this listener-only privacy guarantee. Do not run chat discovery while polling. A remote 409 response stops contention; it is not a cross-machine lock that prevents two processes from starting simultaneously.

Gate 3 scheduler disable/remove and full provider-failure/local-workspace checks remain separate. See the [release checklist](LOCAL-1.0-RELEASE-CHECKLIST.md) and [increment validation](GATE3-TELEGRAM-DIAGNOSTICS.md).
