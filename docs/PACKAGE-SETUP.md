# Install LitBeacon from the release wheel

Download both `litradar-1.0.0-py3-none-any.whl` and `SETUP.txt` from the [v1.0.0 GitHub Release](https://github.com/Light-Danube/LitRadar/releases/tag/v1.0.0), saving them in the **same new writable folder**. If you chose GitHub's **Code → Download ZIP** instead and see `cli.py`, `pyproject.toml` and `.bat` files, follow the [Windows source-ZIP guide](WINDOWS-SOURCE-ZIP.md). The exact uploaded wheel passed a fresh Linux installed-package smoke; [release checks](LOCAL-1.0-RELEASE-CHECKLIST.md) record the platform limits. Until the release `SETUP.txt` is replaced, use the commands on this page, especially `--no-cache-dir` on Windows.

You need Python **3.11 or newer** (3.12 recommended) and internet for pip dependencies. Git, Node, Docker, models, API keys and the source checkout are unnecessary for the already built wheel. The commands below set `LITBEACON_HOME` to a new `user-data` folder for a disposable trial, so an existing LitBeacon library is not opened. Keep that folder if you want to retain trial data.

## Windows 10/11 — PowerShell

1. Install Python **3.12.x** from [python.org](https://www.python.org/downloads/windows/) if needed; select 3.12 even if the site offers a newer version. Python 3.12.7 is suitable. Check `py -3.12 --version`. Save both release files in a new writable folder, such as `Documents\LitBeacon-1.0.0-test`; open PowerShell **in that folder**. Confirm that `SETUP.txt` and the wheel are present.
2. Run without activating PowerShell scripts:

   ```powershell
   py -3.12 -m venv .venv
   $env:LITBEACON_HOME = (Join-Path (Get-Location) 'user-data')
   .\.venv\Scripts\python.exe -m pip install --no-cache-dir ".\litradar-1.0.0-py3-none-any.whl[web]"
   .\.venv\Scripts\python.exe -m pip check
   .\.venv\Scripts\python.exe -m cli --version
   .\.venv\Scripts\python.exe -m cli init
   .\.venv\Scripts\python.exe -m cli web
   ```

3. Open <http://127.0.0.1:8765>, confirm the page says `v1.0.0`, then stop with Ctrl+C. Restart with the final command in the same PowerShell window; set `LITBEACON_HOME` again in a new window. If the port is occupied, use `-m cli web --port 8787` and open that port. The wheel has no `run_litbeacon_web.bat`; launchers belong to the source checkout.

If `py -3.12` fails, confirm the launcher was installed with Python and run `py --list`. The Windows pip command disables the pip cache. If a permission error remains, use a fresh writable download folder and report the command, Python version and first safe error line without sharing private paths, a library, `.env`, tokens or logs. [Platform validation status](LOCAL-1.0-RELEASE-CHECKLIST.md).

## macOS — Terminal

1. Install Python **3.12.x** from [python.org](https://www.python.org/downloads/macos/) if needed; check `python3 --version` (3.11+). The system Python may be too old. Save both release files in a new writable folder and open Terminal there.
2. Run:

   ```sh
   python3 -m venv .venv
   export LITBEACON_HOME="$PWD/user-data"
   ./.venv/bin/python -m pip install './litradar-1.0.0-py3-none-any.whl[web]'
   ./.venv/bin/python -m pip check
   ./.venv/bin/python -m cli --version
   ./.venv/bin/python -m cli init
   ./.venv/bin/python -m cli web
   ```

3. Open <http://127.0.0.1:8765>; stop with Ctrl+C and restart with the same command in the same terminal. Export `LITBEACON_HOME` again in a new terminal. The wheel is pure Python, but dependencies still need macOS wheels compatible with your Python and CPU. **Native macOS installation and browser behavior remain unverified** for this candidate.

## Linux — terminal

1. Check `python3 --version` (3.11+). If `venv` reports missing `ensurepip`, install your distribution's Python venv package (for example `python3-venv` on Debian/Ubuntu). Save both release files in a new writable folder and open a terminal there.
2. Run:

   ```sh
   python3 -m venv .venv
   export LITBEACON_HOME="$PWD/user-data"
   ./.venv/bin/python -m pip install './litradar-1.0.0-py3-none-any.whl[web]'
   ./.venv/bin/python -m pip check
   ./.venv/bin/python -m cli --version
   ./.venv/bin/python -m cli init
   ./.venv/bin/python -m cli web
   ```

3. Open <http://127.0.0.1:8765>; stop with Ctrl+C. Export `LITBEACON_HOME` again in a new terminal before restarting. The Linux installed-wheel smoke checks packaged web assets, but a headless check cannot establish native browser appearance or every distribution's dependency compatibility.

## Data, optional components and upgrades

The browser binds to localhost and has no login; do not expose it to a LAN or the internet. Dependencies and explicit scholarly searches use the network; saved-library operations are local. No provider or model is needed for first launch.

Outside the isolated trial above, installed data defaults to `%LOCALAPPDATA%\LitBeacon` on Windows, `~/Library/Application Support/LitBeacon` on macOS, and `$XDG_DATA_HOME/LitBeacon` (usually `~/.local/share/LitBeacon`) on Linux. `LITBEACON_HOME` must be set before each new process; the trial `user-data` folder can be removed only when you no longer need its data. An installed wheel does not copy an older source-checkout library. See [wheel data locations](USER-GUIDE.md#wheel-installation) and [backup/restore](USER-GUIDE.md#consistent-local-backup-and-restore).

For optional TUI/file imports, replace `[web]` in the pip command with `[web,ui,annotations]`, then run `-m cli ui` with the same venv interpreter. LLMs, Telegram and local embeddings need separate deliberate setup. Windows Task Scheduler installation and `.bat` launchers require a source checkout; wheel users can configure their own scheduler. [User guide](USER-GUIDE.md) · [network use](NETWORK-USE.md) · [logging](LOGGING.md).

A virtual environment is tied to its original Python installation: installing Python 3.12 does not convert an old `.venv`. For a source checkout, the LitBeacon launchers preserve a mismatched/broken environment as `.venv-before-python312` and create a new `.venv`; for a wheel install, save the new release files in a new folder and create a new `.venv` there. Keep old environments until you have confirmed the new install.

To upgrade from v0.8.0, **stop all LitBeacon processes and back up first**. Use the old environment's `-m cli library-backup NEW_BACKUP_DIRECTORY` if available; elect Research/offline files explicitly with writers stopped, and save profile/digest settings and credentials separately. If the old release lacks that command, install the new wheel in a **separate venv** and run `-m cli --db OLD_DATABASE library-backup NEW_BACKUP_DIRECTORY` *before* `init` or `web`; this opens the old database read-only. Keep the backup outside the setup folder. Then install into a new folder and use the same per-user data location if you intend to upgrade that library. `init` applies additive migrations; source-checkout libraries are not moved automatically. Never delete an old data directory to repair an install. [Recovery details](USER-GUIDE.md#consistent-local-backup-and-restore).

A source checkout does not include the published wheel. [Release verification status](LOCAL-1.0-RELEASE-CHECKLIST.md).
