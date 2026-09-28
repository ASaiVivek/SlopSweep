"""Path containment, root guard, git skip, and run locking."""

from __future__ import annotations

import errno
import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from slopsweep.config import LOCK_NAME, MARKER_NAME

EXIT_REFUSED = 3


class SafetyError(Exception):
    """Operation refused by a safety rule."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class ResolvedRoot:
    path: Path


def is_filesystem_root(path: Path) -> bool:
    resolved = path.resolve()
    if resolved == Path("/"):
        return True
    if os.name == "nt":
        return len(resolved.parts) <= 1
    parent = resolved.parent
    return parent == resolved


def validate_root(root: Path, *, home: Path | None = None) -> ResolvedRoot:
    """Ensure root is safe to use and contains the marker file."""
    home_path = (home if home is not None else Path.home()).resolve()
    try:
        resolved = root.expanduser().resolve()
    except OSError as exc:
        raise SafetyError(f"cannot resolve root: {root}") from exc

    if is_filesystem_root(resolved):
        raise SafetyError("refusing filesystem root as workspace")
    if resolved == home_path:
        raise SafetyError("refusing home directory as workspace")
    marker = resolved / MARKER_NAME
    if not marker.is_file():
        raise SafetyError(f"missing marker {MARKER_NAME}; run slopsweep init first")
    return ResolvedRoot(path=resolved)


def realpath_inside_root(root: Path, path: Path) -> Path:
    """Resolve path and ensure it is strictly inside root (symlinks not followed)."""
    root_real = os.path.realpath(root)
    candidate = path if path.is_absolute() else (root / path)
    if lstat_is_symlink(candidate):
        parent_real = os.path.realpath(candidate.parent)
        link_path = os.path.join(parent_real, candidate.name)
    else:
        link_path = os.path.realpath(candidate)
    root_prefix = root_real.rstrip(os.sep) + os.sep
    if link_path != root_real and not link_path.startswith(root_prefix):
        raise SafetyError(f"path escapes workspace: {path}")
    return Path(link_path)


def lstat_is_symlink(path: Path) -> bool:
    try:
        return stat.S_ISLNK(path.lstat().st_mode)
    except OSError:
        return False


def is_git_tracked_or_in_work_tree(root: Path, path: Path) -> bool:
    """True if path is inside a git work tree within root."""
    inside = realpath_inside_root(root, path)
    current = inside
    root_real = os.path.realpath(root)
    while True:
        git_dir = current / ".git"
        if git_dir.exists():
            return True
        if os.path.realpath(current) == root_real:
            break
        parent = current.parent
        if parent == current:
            break
        current = parent
    return False


def iter_safe_paths(root: Path, directory: Path) -> Iterator[Path]:
    """Walk directory without following symlinks; yield file paths inside root."""
    dir_real = realpath_inside_root(root, directory)
    if lstat_is_symlink(directory):
        return
    for dirpath, dirnames, filenames in os.walk(dir_real, topdown=True, followlinks=False):
        dir_path = Path(dirpath)
        # Do not descend into symlinks
        dirnames[:] = [
            name for name in dirnames if not lstat_is_symlink(dir_path / name)
        ]
        for name in filenames:
            child = dir_path / name
            if lstat_is_symlink(child):
                yield child
                continue
            try:
                realpath_inside_root(root, child)
            except SafetyError:
                continue
            yield child


@contextmanager
def run_lock(root: Path) -> Iterator[None]:
    lock_path = root / LOCK_NAME
    fd: int | None = None
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise SafetyError("another slopsweep run is in progress") from exc
        raise SafetyError(f"cannot acquire lock: {exc}") from exc
    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass


def refuse_symlink_target_outside(root: Path, path: Path) -> None:
    """Raise if symlink points outside root."""
    if not lstat_is_symlink(path):
        return
    link_text = os.readlink(path)
    if os.path.isabs(link_text):
        target = Path(link_text)
    else:
        target = (path.parent / link_text).resolve()
    realpath_inside_root(root, target)
