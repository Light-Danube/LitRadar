"""Package an already-built wheel with a short standalone setup guide."""
from __future__ import annotations

import argparse
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
import re
import stat
import tomllib
from zipfile import BadZipFile, ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
MAX_WHEEL_BYTES = 50 * 1024 * 1024
REQUIRED = {
    'cli.py', 'config.py', 'workspace_web.py', 'storage/recovery.py',
    'litradar_runtime/__init__.py', 'litradar_runtime/ui.tcss', 'litradar_runtime/assets/VERSION',
    'litradar_runtime/assets/research_profile.json', 'litradar_runtime/assets/digest_config.json',
    'web/index.html', 'web/static/app.js', 'web/static/styles.css',
    'web/static/brand/litbeacon-mark.png',
}


def wheel_version(wheel: Path, tag: str | None = None) -> str:
    if wheel.is_symlink() or not wheel.is_file() or wheel.stat().st_size > MAX_WHEEL_BYTES:
        raise ValueError('Select a regular built wheel of at most 50 MiB')
    if not re.fullmatch(r'litradar-[A-Za-z0-9_.+!-]+\.whl', wheel.name):
        raise ValueError('Expected a LitRadar wheel filename')
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    modules = {name + '.py' for name in project['tool']['setuptools']['py-modules']}
    packages = set(project['tool']['setuptools']['packages'])
    with ZipFile(wheel) as archive:
        names = archive.namelist()
        if len(names) > 2000 or len(names) != len(set(names)) or not REQUIRED <= set(names):
            raise ValueError('Missing runtime assets, duplicate entries or oversized wheel inventory')
        metadata = [name for name in names if name.endswith('.dist-info/METADATA')]
        if len(metadata) != 1:
            raise ValueError('Expected one distribution metadata record')
        info_root = metadata[0].split('/')[0]
        total = 0
        for item in archive.infolist():
            path = PurePosixPath(item.filename)
            total += item.file_size
            if (path.is_absolute() or '..' in path.parts or '\\' in item.filename
                    or ':' in item.filename or stat.S_ISLNK(item.external_attr >> 16)
                    or total > MAX_WHEEL_BYTES):
                raise ValueError('Unsafe or oversized wheel entry')
            if not path.parts or not (item.filename in modules or path.parts[0] in packages | {info_root}):
                raise ValueError('Wheel contains unrelated source/development files')
            if (path.name.startswith('.env') or '__pycache__' in path.parts
                    or any(part.casefold() in {'log', 'logs'} for part in path.parts)
                    or re.search(r'\.log(?:\..*)?$', path.name, re.IGNORECASE)
                    or item.filename.endswith(('.sqlite', '.sqlite3', '.sqlite3-wal', '.sqlite3-shm',
                                               '.pdf', '.log', '.safetensors'))):
                raise ValueError('Wheel contains excluded local data')
        metadata_record = BytesParser().parsebytes(archive.read(metadata[0]))
        if metadata_record.get_all('Name') != ['litradar'] or len(metadata_record.get_all('Version', [])) != 1:
            raise ValueError('Expected LitRadar distribution metadata')
        version = metadata_record['Version']
        canonical = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
        if (not re.fullmatch(r'[0-9][A-Za-z0-9_.+!-]*', version)
                or version != canonical or version != project['project']['version']
                or archive.read('litradar_runtime/assets/VERSION').decode('utf-8').strip() != version):
            raise ValueError('Source, package and bundled version must agree')
        if wheel.name.split('-')[1] != version:
            raise ValueError('Wheel filename must match package version')
        if tag is not None and tag.removeprefix('v') != version:
            raise ValueError('Release tag must match the built package version')
    return version


def setup_text(wheel_name: str, version: str) -> str:
    return f'''LitBeacon {version} - package setup

Requirements: Python 3.11+; Python 3.12 is recommended and tested.
Python 3.12.7 is suitable. Internet access is needed for pip dependencies.
Extract both files together into a writable folder. No Git, Node, Docker,
development checkout, legacy documentation or credentials are needed.
Local-only describes library use; provider searches and dependency installation use the network.

WINDOWS - open PowerShell in this extracted folder:
  py -3.12 --version
  py -3.12 -m venv .venv
  .\\.venv\\Scripts\\python.exe -m pip install ".\\{wheel_name}[web]"
  .\\.venv\\Scripts\\python.exe -m pip check
  .\\.venv\\Scripts\\python.exe -m cli --version
  .\\.venv\\Scripts\\python.exe -m cli init
  .\\.venv\\Scripts\\python.exe -m cli web

LINUX / MACOS - open a terminal in this extracted folder:
  python3 --version
  python3 -m venv .venv
  ./.venv/bin/python -m pip install "./{wheel_name}[web]"
  ./.venv/bin/python -m pip check
  ./.venv/bin/python -m cli --version
  ./.venv/bin/python -m cli init
  ./.venv/bin/python -m cli web

If py -3.12 is unavailable, install Python 3.12 from python.org and reopen
PowerShell. Python 3.11 users can replace -3.12 with -3.11 in both commands.
Do not use py -3: it can silently select a different installed version.
On Linux/macOS, confirm python3 --version is 3.11 or newer before creating .venv.
Open http://127.0.0.1:8765. Stop with Ctrl+C; restart using the same web command.
The server is for localhost use; do not expose it publicly or on a LAN.
For help, use the same venv interpreter with: -m cli --help
Optional TUI/file parsers: install this wheel with [web,ui,annotations] instead.
Models, cloud LLMs and Telegram are optional; nothing requires them for local library use.

DATA AND UPDATES
Windows data: %LOCALAPPDATA%\\LitBeacon
Linux data: $XDG_DATA_HOME/LitBeacon (default ~/.local/share/LitBeacon)
macOS data: ~/Library/Application Support/LitBeacon
Set LITBEACON_HOME before launching to choose another data directory.
Missing editable defaults are seeded; existing profiles/configuration are retained.
New application file logs belong in this data directory under log/, never in installed code.
Optional Telegram diagnostics: -m cli telegram-run --debug --log-file telegram-listener.log
This writes log/telegram-listener.log under that data directory; logs are not release files.
Existing source-checkout libraries are not moved: use --db PATH before the command.

Before upgrading, stop writers and use the OLD environment's interpreter with:
  -m cli library-backup NEW_BACKUP_DIRECTORY
This is a database-only backup. Elect research/offline roots explicitly when needed;
see library-backup --help. Keep profile/digest settings and credentials separately.
If the old release lacks library-backup, install the new wheel in a separate venv,
then use its interpreter with -m cli --db OLD_DATABASE library-backup NEW_DIRECTORY
BEFORE init or web. The backup opens the selected source read-only, without migrations.
Extract a later setup ZIP into a new folder and repeat setup. The same per-user
library remains in place; init applies additive migrations, so back up first.
Uninstalling/removing the environment does not remove your separate library.
Built-in Windows Task Scheduler setup still requires the source checkout;
package users may configure their own scheduler with -m cli scheduled-run.

Windows/macOS/Linux guide and known limits:
https://github.com/Light-Danube/LitRadar/blob/main/docs/PACKAGE-SETUP.md
This package has not been verified on every operating system or Python version.
Installing this package does not approve a new release or certify venue/index metadata.
'''


def build_bundle(wheel: Path, output_dir: Path, *, tag: str | None = None) -> Path:
    version = wheel_version(wheel, tag)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f'LitBeacon-{version}-setup.zip'
    # Reserve exclusively: a repeated build must never replace an existing artifact.
    with target.open('xb') as handle:
        try:
            with ZipFile(handle, 'w', ZIP_DEFLATED) as archive:
                archive.write(wheel, wheel.name)
                archive.writestr('SETUP.txt', setup_text(wheel.name, version))
        except BaseException:
            handle.close()
            target.unlink(missing_ok=True)
            raise
    return target


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel', type=Path)
    parser.add_argument('--output-dir', type=Path, default=Path('dist'))
    parser.add_argument('--tag', help='optional release tag; must match package metadata')
    args = parser.parse_args(argv)
    try:
        print(build_bundle(args.wheel, args.output_dir, tag=args.tag))
    except (ValueError, OSError, BadZipFile) as exc:
        parser.exit(1, f'Package setup build failed: {exc}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
