# Small package setup

For releases that provide `LitBeacon-<version>-setup.zip`, download and extract that asset. It contains only the built runtime wheel and a standalone `SETUP.txt` with exact commands for that wheel. GitHub's automatic source archives remain available for developers; ordinary users do not need them, legacy docs, tests or the repository checkout.

Requirements: **Python 3.11+** and internet access for pip dependency installation. Local-only does not mean an offline installer. The default `[web]` installation excludes development/browser tests, embeddings, cloud LLM SDKs and TUI/file-parser extras.

Open `SETUP.txt` in the extracted folder. On Windows its commands create `.venv` and invoke `.venv\Scripts\python.exe` directly, without PowerShell activation-policy changes. Linux/macOS use `.venv/bin/python`. Install the named wheel, then run:

```sh
python -m cli init
python -m cli web
```

Use the environment's Python for those commands. Open **http://127.0.0.1:8765**, stop with Ctrl+C and restart with the same web command. No credentials or models are needed to use a saved local library. Network provider requests remain explicit.

Installed data lives in the per-user LitBeacon directory, separately from the extracted package and environment. Existing source-checkout libraries are not moved automatically. See [data locations and overrides](USER-GUIDE.md#wheel-installation) and [consistent backup/restore](USER-GUIDE.md#consistent-local-backup-and-restore-unreleased). Back up with the old environment before updating; keep profiles/digest settings/credentials separately, extract a new version into a new folder and repeat setup. Never delete the data directory to repair an installation.

If the older release has no `library-backup` command, install the new wheel into a separate environment first. Before running `init`/`web`, use its interpreter with `-m cli --db OLD_DATABASE library-backup NEW_BACKUP_DIRECTORY`. That command snapshots the selected old library read-only without migrating it. Elect durable Research/offline roots explicitly and keep writers stopped while including those files.

Optional TUI and file adapters can be selected as `[web,ui,annotations]`. Built-in Windows Task Scheduler installation still requires the source checkout; package users can configure their own scheduler for `python -m cli scheduled-run`.

## Build and review a future package

From a clean source checkout:

```sh
python -m pip wheel --no-deps --wheel-dir dist .
python -m scripts.build_user_bundle dist/litradar-0.8.0-py3-none-any.whl --output-dir dist
```

Replace the example wheel filename with the one just built. The builder derives the setup archive name and exact guide commands from wheel metadata. Root VERSION, pyproject metadata and bundled VERSION must agree; `--tag v<version>` additionally checks an approved release tag. Existing setup ZIPs are never overwritten.

CI builds the ZIP, verifies that its two entries include a byte-identical wheel, then installs the **extracted** wheel into clean Ubuntu and Windows environments and executes the synthetic CLI/static-assets/web-edit/restart and backup/restore smoke outside the checkout. Recovery checks use disposable SQLite and elected synthetic files, preserving durable rows/histories/tombstones and rejecting overwrites. The setup ZIP is uploaded as a reviewable Actions artifact. A workflow definition alone is not a passing result; use the actual candidate checks.

The release workflow builds and smokes the same package **after an owner publishes a release**, then attaches the wheel and setup ZIP to that existing release. It does not bump versions, create a tag or publish a release. No release is published by this change; version remains 0.8.0. Full release approval remains Gate 6.

New application file logs use the writable LitBeacon user directory's `log/` (checkout users: project `log/`); never write logs beside installed code. Optional Telegram file logging accepts a filename, for example `python -m cli telegram-run --debug --log-file telegram-listener.log`. [Shared logging convention and exclusions](LOGGING.md).
