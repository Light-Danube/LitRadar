"""Bounded local snapshots. Never initialize/migrate the source or merge a restore.

Bundles are directories, not archives. Checksums detect damage, not authenticity;
only restore bundles you created or trust. Filesystem writers must be stopped when
including artifacts because SQLite cannot snapshot separate files atomically.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import time
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

FORMAT = "litbeacon-local-backup"
FORMAT_VERSION = 1
MAX_FILES = 10000
MAX_FILE_BYTES = 1024 ** 3
MAX_TOTAL_BYTES = 4 * 1024 ** 3
MAX_MANIFEST_BYTES = 2 * 1024 ** 2
MAX_SECONDS = 60
EXCLUSIONS = [".env and credentials", "logs and caches", "models and application code",
              "research_profile.json, digest_config.json and scheduler registrations"]
RESEARCH_FILES = {"manifest.json", "search.json", "evidence.json", "matrix.md", "matrix.csv"}
OFFLINE_FILES = {"metadata.json", "abstract.txt", "citation.bib", "notes.txt",
                 "llm_assessment.json", "download_error.txt", "retrieval_status.txt"}
_RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)", re.I)
_FTS_TABLE = """CREATE VIRTUAL TABLE papers_fts USING fts5(
title, abstract, venue, notes, content='papers', content_rowid='id', tokenize='unicode61')"""
_FTS_TRIGGERS = {
    "papers_fts_ai": """CREATE TRIGGER papers_fts_ai AFTER INSERT ON papers BEGIN
    INSERT INTO papers_fts(rowid, title, abstract, venue, notes)
    VALUES (new.id, new.title, new.abstract, new.venue, new.notes); END""",
    "papers_fts_ad": """CREATE TRIGGER papers_fts_ad AFTER DELETE ON papers BEGIN
    INSERT INTO papers_fts(papers_fts, rowid, title, abstract, venue, notes)
    VALUES ('delete', old.id, old.title, old.abstract, old.venue, old.notes); END""",
    "papers_fts_au": """CREATE TRIGGER papers_fts_au AFTER UPDATE OF title, abstract, venue, notes ON papers BEGIN
    INSERT INTO papers_fts(papers_fts, rowid, title, abstract, venue, notes)
    VALUES ('delete', old.id, old.title, old.abstract, old.venue, old.notes);
    INSERT INTO papers_fts(rowid, title, abstract, venue, notes)
    VALUES (new.id, new.title, new.abstract, new.venue, new.notes); END""",
}


def _normalized_sql(value: str) -> str:
    return re.sub(r"\s+", "", value).rstrip(";")


def _is_link(info) -> bool:
    # Python 3.11 has no Path.is_junction(); Windows directory junctions and
    # other reparse points can redirect access without being symbolic links.
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _safe_path(path: str | Path, *, directory: bool = False) -> Path:
    """Reject symlinks in every component, including dangling links."""
    path = Path(os.path.abspath(path))
    for part in [*reversed(path.parents), path]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if _is_link(info):
            raise ValueError("Symlink/junction/reparse-point paths are not allowed")
    if directory and not path.is_dir():
        raise ValueError("An existing directory is required")
    return path


def _relative(value: object) -> str:
    if not isinstance(value, str) or len(value) > 512 or not value:
        raise ValueError("Invalid bundle path")
    parts = value.split("/")
    if any(not p or p in {".", ".."} or p.endswith((".", " ")) or len(p) > 200
           or _RESERVED.match(p) or any(ord(c) < 32 or c in '\\:<>"|?*' for c in p)
           for p in parts):
        raise ValueError("Unsafe bundle path")
    if PurePosixPath(value).is_absolute():
        raise ValueError("Absolute bundle path")
    if value == "library.sqlite3":
        return value
    if len(parts) != 3:
        raise ValueError("Only elected research/offline artifact files are supported")
    group, folder, name = parts
    if folder.startswith(".") or name.startswith("."):
        raise ValueError("Hidden artifact paths are excluded")
    if group == "research" and name in RESEARCH_FILES and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", folder):
        return value
    if group == "offline" and (name in OFFLINE_FILES or name.lower().endswith(".pdf")):
        return value
    raise ValueError("Unsupported artifact file; credentials/caches/logs are excluded")


def _reader(path: Path):
    _safe_path(path)
    before = path.lstat()
    if _is_link(before) or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise ValueError("Only regular, non-linked files are allowed")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0))
    handle = os.fdopen(fd, "rb")
    after = os.fstat(fd)
    if _is_link(after) or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
        handle.close()
        raise ValueError("File changed while opening")
    return handle


def _copy(source: Path, destination: Path | None, *, limit: int = MAX_FILE_BYTES) -> dict:
    digest = hashlib.sha256()
    count = 0
    deadline = time.monotonic() + MAX_SECONDS
    with _reader(source) as reader:
        before = os.fstat(reader.fileno())
        writer = destination.open("xb") if destination is not None else None
        try:
            if writer is not None:
                os.chmod(destination, 0o600)
            while chunk := reader.read(min(1024 * 1024, limit - count + 1)):
                count += len(chunk)
                if count > limit or time.monotonic() > deadline:
                    raise ValueError("File exceeds backup size/time bounds")
                digest.update(chunk)
                if writer is not None:
                    writer.write(chunk)
            after = os.fstat(reader.fileno())
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("Artifact changed; stop all writers and retry")
        finally:
            if writer is not None:
                writer.close()
    return {"size": count, "sha256": digest.hexdigest()}


def _files(root: Path, *, max_files: int | None = None) -> list[str]:
    max_files = MAX_FILES if max_files is None else max_files
    result = []
    dirs = [root]
    visited = 0
    while dirs:
        folder = dirs.pop()
        _safe_path(folder, directory=True)
        with os.scandir(folder) as entries:
            for entry in entries:
                visited += 1
                if visited > MAX_FILES * 3:
                    raise ValueError("Too many bundle entries")
                if _is_link(entry.stat(follow_symlinks=False)):
                    raise ValueError("Symlink/junction/reparse-point artifact or bundle entry")
                if entry.is_dir(follow_symlinks=False):
                    if len(Path(entry.path).relative_to(root).parts) > 3:
                        raise ValueError("Artifact directories exceed depth bound")
                    dirs.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    result.append(Path(entry.path).relative_to(root).as_posix())
                    if len(result) > max_files:
                        raise ValueError("Too many bundle files")
                else:
                    raise ValueError("Special files are not supported")
    return sorted(result)


def _reserve(path: str | Path) -> Path:
    path = _safe_path(path)
    _safe_path(path.parent, directory=True)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise ValueError("Destination already exists; choose a new directory") from exc
    return path


def _readonly(path: Path, *, immutable: bool = False) -> sqlite3.Connection:
    _safe_path(path)
    if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Missing or oversized SQLite library")
    with _reader(path):
        pass
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(path) + suffix)
        _safe_path(sidecar)
        if sidecar.exists():
            if immutable:
                raise ValueError("Snapshot must not contain SQLite sidecars")
            with _reader(sidecar):
                pass
    uri = path.as_uri() + "?mode=ro" + ("&immutable=1" if immutable else "")
    conn = sqlite3.connect(uri, uri=True, timeout=2)
    try:
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.execute("PRAGMA query_only=ON")
        deadline = time.monotonic() + MAX_SECONDS
        conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 10000)
    except BaseException:
        conn.close()
        raise
    return conn


def _validate_database(path: Path) -> None:
    # An immutable snapshot has no WAL sidecars. No extension loading, user SQL,
    # migrations or application triggers run while inspecting an untrusted bundle.
    with closing(_readonly(path, immutable=True)) as conn:
        for kind, name, sql in conn.execute("SELECT type,name,sql FROM sqlite_schema WHERE sql IS NOT NULL"):
            if kind == "view":
                raise ValueError("Unsupported view in library schema")
            if kind == "trigger" and (name not in _FTS_TRIGGERS or _normalized_sql(sql) != _normalized_sql(_FTS_TRIGGERS[name])):
                raise ValueError("Unsupported trigger in library schema")
            if kind == "table" and re.match(r"CREATE\s+VIRTUAL\s+TABLE", sql, re.I) and (
                    name != "papers_fts" or _normalized_sql(sql) != _normalized_sql(_FTS_TABLE)):
                raise ValueError("Unsupported virtual table in library schema")
        row = conn.execute("SELECT type FROM sqlite_schema WHERE name='papers'").fetchone()
        if row != ("table",):
            raise ValueError("Not a LitBeacon/LitRadar library")
        columns = {r[1] for r in conn.execute("PRAGMA table_info(papers)")}
        if not {"id", "source", "title", "title_normalized"} <= columns:
            raise ValueError("Unrecognized library schema")
        if conn.execute("PRAGMA integrity_check").fetchmany(2) != [("ok",)]:
            raise ValueError("SQLite integrity check failed")
        if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise ValueError("SQLite foreign key check failed")


def backup_library(database: str | Path, destination: str | Path, *,
                   research: str | Path | None = None, offline: str | Path | None = None,
                   writers_stopped: bool = False) -> Path:
    """Read-only source snapshot, plus explicitly selected stopped-writer artifacts."""
    source = _safe_path(database)
    roots = {name: _safe_path(root, directory=True) for name, root in
             (("research", research), ("offline", offline)) if root is not None}
    if roots and not writers_stopped:
        raise ValueError("Including artifacts requires explicit writers-stopped acknowledgement")
    target = _safe_path(destination)
    if any(root == target or root in target.parents or target in root.parents for root in roots.values()):
        raise ValueError("Backup destination must be outside artifact roots")
    if target == source or target in source.parents:
        raise ValueError("Backup destination overlaps the source database")
    bundle = _reserve(target)
    try:
        snapshot = bundle / "library.sqlite3"
        deadline = time.monotonic() + MAX_SECONDS
        def progress(status, remaining, total):
            if total * page_size > MAX_FILE_BYTES or time.monotonic() > deadline:
                raise ValueError("SQLite backup exceeds size/time bounds")
        with closing(_readonly(source)) as reader, closing(sqlite3.connect(snapshot)) as writer:
            page_size = reader.execute("PRAGMA page_size").fetchone()[0]
            if reader.execute("PRAGMA page_count").fetchone()[0] * page_size > MAX_FILE_BYTES:
                raise ValueError("SQLite backup exceeds size bound")
            reader.backup(writer, pages=256, progress=progress, sleep=0.01)
            writer.execute("PRAGMA journal_mode=DELETE")
        os.chmod(snapshot, 0o600)
        _validate_database(snapshot)
        entries = [{"path": "library.sqlite3", **_copy(snapshot, None)}]
        total = entries[0]["size"]
        for group, root in roots.items():
            for name in _files(root):
                relative = _relative(f"{group}/{name}")
                if len(entries) >= MAX_FILES:
                    raise ValueError("Too many backup files")
                dest = bundle / relative
                dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                item = _copy(root / name, dest, limit=min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - total))
                entries.append({"path": relative, **item})
                total += item["size"]
        manifest = {"format": FORMAT, "version": FORMAT_VERSION,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "database": "library.sqlite3", "included_artifacts": sorted(roots),
                    "artifact_writers_stopped": bool(roots and writers_stopped),
                    "excluded": EXCLUSIONS, "files": entries}
        encoded = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
        if len(encoded) > MAX_MANIFEST_BYTES:
            raise ValueError("Manifest exceeds size bound")
        with (bundle / "manifest.json").open("xb") as handle:
            os.chmod(handle.name, 0o600)
            handle.write(encoded)
        # Apply the same portability/collision/manifest rules used by restore.
        # A successful backup must never be a bundle that restore would reject.
        _manifest(bundle)
        return bundle
    except BaseException:
        shutil.rmtree(bundle)
        raise


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate manifest key")
        result[key] = value
    return result


def _manifest(bundle: Path) -> dict:
    path = bundle / "manifest.json"
    with _reader(path) as handle:
        raw = handle.read(MAX_MANIFEST_BYTES + 1)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ValueError("Manifest exceeds size bound")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("Invalid backup manifest") from exc
    if not isinstance(value, dict) or value.get("format") != FORMAT or type(value.get("version")) is not int or value["version"] != FORMAT_VERSION:
        raise ValueError("Unsupported backup manifest format/version")
    if value.get("database") != "library.sqlite3":
        raise ValueError("Invalid backup database path")
    entries = value.get("files")
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_FILES:
        raise ValueError("Invalid manifest file count")
    seen, directories, total = set(), {}, 0
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
            raise ValueError("Invalid manifest file entry")
        path = _relative(item["path"])
        key = path.casefold()
        if key in seen:
            raise ValueError("Duplicate/case-colliding manifest path")
        seen.add(key)
        parent = str(PurePosixPath(path).parent)
        if parent != ".":
            previous = directories.setdefault(parent.casefold(), parent)
            if previous != parent:
                raise ValueError("Case-colliding artifact directories")
        if type(item["size"]) is not int or not 0 <= item["size"] <= MAX_FILE_BYTES:
            raise ValueError("Invalid manifest file size")
        if not isinstance(item["sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) is None:
            raise ValueError("Invalid SHA-256 checksum")
        total += item["size"]
    if total > MAX_TOTAL_BYTES:
        raise ValueError("Backup exceeds total size bound")
    if "library.sqlite3" not in seen:
        raise ValueError("Backup database is missing")
    if set(_files(bundle, max_files=MAX_FILES + 1)) != {"manifest.json", *(i["path"] for i in entries)}:
        raise ValueError("Missing or unexpected bundle files")
    groups = sorted({i["path"].split("/")[0] for i in entries if i["path"] != "library.sqlite3"})
    included = value.get("included_artifacts")
    if not isinstance(included, list) or any(not isinstance(g, str) or g not in {"research", "offline"} for g in included) or len(included) != len(set(included)) or not set(groups) <= set(included):
        raise ValueError("Invalid elected artifact groups")
    if included and value.get("artifact_writers_stopped") is not True:
        raise ValueError("Artifact consistency acknowledgement is missing")
    return value


def restore_library(bundle: str | Path, destination: str | Path) -> Path:
    """Validate and restore into an exclusively reserved new directory only."""
    bundle = _safe_path(bundle, directory=True)
    manifest = _manifest(bundle)
    target = _safe_path(destination)
    if bundle == target or bundle in target.parents or target in bundle.parents:
        raise ValueError("Restore destination overlaps backup")
    restored = _reserve(target)
    try:
        for item in manifest["files"]:
            relative = item["path"]
            dest = restored / relative
            dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            actual = _copy(bundle / relative, dest, limit=item["size"])
            if actual != {"size": item["size"], "sha256": item["sha256"]}:
                raise ValueError("Backup checksum or size mismatch")
        snapshot = restored / "library.sqlite3"
        _validate_database(snapshot)
        snapshot.rename(restored / "litradar.sqlite3")
        return restored / "litradar.sqlite3"
    except BaseException:
        shutil.rmtree(restored)
        raise
