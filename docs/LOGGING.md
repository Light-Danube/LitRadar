# Local application logs

All new or extended application file logging uses the shared `litradar_runtime.LOG_ROOT` and `resolve_log_path()` helper. This convention applies to CLI, web, Textual TUI, Telegram and provider integrations.

- Source checkout: `<project>/log/`.
- Installed wheel: `<LitBeacon user directory>/log/`; use the [documented user directory](USER-GUIDE.md#wheel-installation), including `LITBEACON_HOME` if explicitly configured.
- File logging remains opt-in. Importing the application and using console-only diagnostics do not create the log directory.

For Telegram, run:

```sh
python -m cli telegram-run --debug --log-file telegram-listener.log
```

The filename resolves to `log/telegram-listener.log` under the application workspace, regardless of the current directory. The `log/filename` spelling is also accepted. Absolute paths must remain inside that log directory; traversal and symlink/junction escapes are rejected. Use separate files per process. File rotation stays UTF-8, 1 MiB per file and three backups. This change does not automatically move old files.

Generated logs and rotations are local data: `log/`, legacy `logs/`, `*.log` and `*.log.*` are ignored by Git and excluded from Docker build contexts. The setup ZIP contains only its validated runtime wheel and guide; wheel validation rejects log directories and rotated log files even under a runtime package. Do not force-add logs to Git or attach them automatically to a release. Review and sanitize any diagnostics before sharing.

Extended scheduled-run logging now uses the shared `log/` directory too. Historical `logs/` files remain untouched and ignored; no existing files are moved or deleted. Compose retains its old mount and adds the new directory. Scheduled command output retains its separate behavior; this does not enable global file logging or promise that every legacy output stream is sanitized.

New file diagnostics must omit credentials, authenticated URLs, raw request/response bodies and private research/message content. `sources.http.format_provider_error()` supplies fixed actionable provider-error messages without reading remote response bodies or rendering exception text. Registry progress, search summaries, citation failure history, scan failure summaries and Research API transport errors use it. Retries, exception objects and partial-provider success remain unchanged.

This is a bounded safety improvement. Stored scan configuration/query context, existing provider results, offline-download `download_error.txt` reports, independent digest/chat-discovery transports and scheduler subprocess output retain their separate behavior. Do not treat the entire application output as a sanitized log stream. See [Telegram-specific diagnostics](TELEGRAM-TROUBLESHOOTING.md) and [provider-failure validation](archive/release-1.0/evidence/GATE3-PROVIDER-FAILURES.md).
