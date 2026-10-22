"""Read explicitly selected bibliography files beneath a chosen directory.

No directory enumeration, recursion, URL resolution or parser path access.
"""
from __future__ import annotations

import os
from pathlib import Path, PureWindowsPath
import stat

FORMATS = {'.ris': 'ris', '.bib': 'bibtex', '.bibtex': 'bibtex', '.pdf': 'pdf'}


class LocalPathError(ValueError):
    pass


def _linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) &
                                            getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400))


def _check_components(path):
    for component in reversed((path, *path.parents)):
        info = component.lstat()
        if _linked(info):
            raise LocalPathError('Linked or redirected input paths are not supported')


def _selection(root, names):
    from .local_import import MAX_FILES
    if not isinstance(names, (tuple, list)) or not 1 <= len(names) <= MAX_FILES:
        raise LocalPathError(f'Select 1–{MAX_FILES} individual files')
    if str(root).startswith(('\\\\', '//')):
        raise LocalPathError('Network input roots are not supported')
    chosen = Path(root).absolute()
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        drive_type = ctypes.WinDLL('kernel32', use_last_error=True).GetDriveTypeW
        drive_type.argtypes = [wintypes.LPCWSTR]
        drive_type.restype = wintypes.UINT
        if drive_type(chosen.anchor) == 4:  # DRIVE_REMOTE includes mapped shares
            raise LocalPathError('Network input roots are not supported')
    _check_components(chosen)
    if not chosen.is_dir():
        raise LocalPathError('Choose a regular directory as the input root')
    selections = []
    for name in names:
        if not isinstance(name, str) or not name or len(name) > 1000 or '\x00' in name:
            raise LocalPathError('Invalid relative filename')
        # Reject Windows drive/UNC/ADS syntax even on POSIX.
        parts = name.replace('\\', '/').split('/')
        if PureWindowsPath(name).drive or name.startswith(('/', '\\')) or ':' in name or any(p in {'', '.', '..'} for p in parts):
            raise LocalPathError('Select relative filenames within the chosen root; traversal is not supported')
        relative = Path(*parts)
        kind = FORMATS.get(relative.suffix.casefold())
        if kind is None:
            raise LocalPathError('Choose RIS, BibTeX or PDF files; directories and archives are not supported')
        selections.append((relative, kind))
    return chosen, selections


def _posix_open(root, relative):
    # Anchor every directory component using no-follow handles. A rename cannot
    # redirect the final open through a substituted parent symlink.
    if not (hasattr(os, 'O_NOFOLLOW') and os.open in os.supports_dir_fd):
        raise LocalPathError('This platform cannot safely open selected input paths')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open(root.anchor, flags)
    try:
        for part in (*root.parts[1:], *relative.parts[:-1]):
            next_directory = os.open(part, flags, dir_fd=directory)
            os.close(directory)
            directory = next_directory
        fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, 'O_NONBLOCK', 0),
                     dir_fd=directory)
        return fd
    finally:
        os.close(directory)


def _windows_open(root, relative):  # exercised on native Windows separately
    import ctypes
    from ctypes import wintypes
    import msvcrt
    path = root / relative
    _check_components(path)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = kernel.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    final = kernel.GetFinalPathNameByHandleW
    final.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    final.restype = wintypes.DWORD
    # OPEN_REPARSE_POINT avoids following a final symlink. Parent changes are
    # caught by comparing the opened handle's actual location before reading.
    handle = create(str(path), 0x80000000, 1, None, 3, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise LocalPathError('Selected file could not be safely opened')
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        length = final(handle, buffer, len(buffer), 0)
        if not length or length >= len(buffer):
            raise LocalPathError('Selected file location could not be verified')
        actual = buffer.value
        if actual.startswith('\\\\?\\UNC\\'):
            actual = '\\\\' + actual[8:]
        elif actual.startswith('\\\\?\\'):
            actual = actual[4:]
        if os.path.normcase(os.path.abspath(actual)) != os.path.normcase(os.path.abspath(path)):
            raise LocalPathError('Selected file was redirected outside its expected location')
        fd = msvcrt.open_osfhandle(int(handle), os.O_RDONLY | os.O_BINARY)
        handle = None  # ownership transferred to fd
        return fd
    finally:
        if handle is not None:
            close(handle)


def read_selected_files(root, names):
    """Return capped bytes plus basename/format; never return absolute paths."""
    from .local_import import MAX_FILE_BYTES, MAX_TOTAL_BYTES
    try:
        chosen, selections = _selection(root, names)
        files, total = [], 0
        for relative, kind in selections:
            candidate = chosen / relative
            _check_components(candidate)
            before = candidate.lstat()
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise LocalPathError('Selected input must be a regular non-linked file')
            if not 1 <= before.st_size <= MAX_FILE_BYTES:
                raise LocalPathError('Each selected file must contain 1 byte–5 MB')
            fd = _windows_open(chosen, relative) if os.name == 'nt' else _posix_open(chosen, relative)
            with os.fdopen(fd, 'rb') as stream:
                opened = os.fstat(stream.fileno())
                if _linked(opened) or not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                    raise LocalPathError('Selected input must be a regular non-linked file')
                if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                    raise LocalPathError('Selected file changed while opening; preview again')
                content = stream.read(MAX_FILE_BYTES + 1)
                after = os.fstat(stream.fileno())
                if (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                    raise LocalPathError('Selected file changed while reading; preview again')
            total += len(content)
            if not content or len(content) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
                raise LocalPathError('Selected files exceed the 5 MB/file or 10 MB/batch limit')
            files.append({'filename': relative.name, 'format': kind, 'content': content})
        return files
    except LocalPathError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise LocalPathError('Selected local files are unavailable or unsafe; check the chosen root and files') from exc
