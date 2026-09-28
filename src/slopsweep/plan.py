"""Compute cleanup actions without mutating the filesystem."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

from slopsweep.config import Config
from slopsweep.manifest import load_manifest
from slopsweep.safety import (
    is_git_tracked_or_in_work_tree,
    iter_safe_paths,
    lstat_is_symlink,
    realpath_inside_root,
)


class ActionKind(StrEnum):
    TRASH = "trash"
    ARCHIVE = "archive"
    PURGE = "purge"


@dataclass(frozen=True)
class PlannedAction:
    kind: ActionKind
    path: Path
    bytes: int
    detail: str = ""


def _file_size(path: Path) -> int:
    try:
        if lstat_is_symlink(path):
            return 0
        return path.lstat().st_size
    except OSError:
        return 0


def _mtime(path: Path) -> datetime:
    ts = path.lstat().st_mtime
    return datetime.fromtimestamp(ts, tz=UTC)


def _trash_dest(root: Path, source: Path, now: datetime) -> Path:
    day = now.astimezone(UTC).strftime("%Y-%m-%d")
    rel = source.relative_to(root)
    return root / ".trash" / day / rel


def _session_meta(session_dir: Path) -> dict[str, object]:
    meta_file = session_dir / ".session.json"
    if not meta_file.is_file():
        return {}
    try:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def session_ended(session_dir: Path) -> bool:
    meta = _session_meta(session_dir)
    ended = meta.get("ended_at")
    return ended is not None and ended != ""


def scratch_eligible(
    session_dir: Path,
    root: Path,
    config: Config,
    now: datetime,
) -> bool:
    if session_ended(session_dir):
        return True
    tmp_dir = session_dir / "tmp"
    if not tmp_dir.is_dir():
        return True
    cutoff = now - timedelta(hours=config.scratch_ttl_hours)
    for path in iter_safe_paths(root, tmp_dir):
        if lstat_is_symlink(path):
            continue
        if _mtime(path) > cutoff:
            return False
    return True


def _plan_manifest_discards(root: Path, now: datetime) -> list[PlannedAction]:
    actions: list[PlannedAction] = []
    sessions_root = root / "sessions"
    if not sessions_root.is_dir():
        return actions
    for session_dir in sorted(sessions_root.iterdir()):
        if not session_dir.is_dir():
            continue
        manifest_file = session_dir / "manifest.jsonl"
        try:
            entries = load_manifest(manifest_file)
        except ValueError:
            continue
        for entry in entries:
            if entry.verdict != "discard":
                continue
            target = session_dir / entry.path
            try:
                real = realpath_inside_root(root, target)
            except Exception:
                continue
            if not (real.exists() or lstat_is_symlink(real)):
                continue
            if is_git_tracked_or_in_work_tree(root, real):
                continue
            actions.append(
                PlannedAction(
                    kind=ActionKind.TRASH,
                    path=real,
                    bytes=_file_size(real),
                    detail=f"manifest discard -> {_trash_dest(root, real, now)}",
                )
            )
    return actions


def _collect_tree_paths(directory: Path, root: Path) -> list[Path]:
    paths: list[Path] = []
    if not directory.exists():
        return paths
    if lstat_is_symlink(directory):
        return paths
    for path in iter_safe_paths(root, directory):
        paths.append(path)
    return paths


def _plan_stale_scratch(root: Path, config: Config, now: datetime) -> list[PlannedAction]:
    actions: list[PlannedAction] = []
    sessions_root = root / "sessions"
    if not sessions_root.is_dir():
        return actions
    for session_dir in sorted(sessions_root.iterdir()):
        if not session_dir.is_dir():
            continue
        tmp_dir = session_dir / "tmp"
        if not scratch_eligible(session_dir, root, config, now):
            continue
        for path in _collect_tree_paths(tmp_dir, root):
            if is_git_tracked_or_in_work_tree(root, path):
                continue
            actions.append(
                PlannedAction(
                    kind=ActionKind.TRASH,
                    path=path,
                    bytes=_file_size(path),
                    detail="stale scratch",
                )
            )
    return actions


def outputs_fully_old(outputs_dir: Path, root: Path, config: Config, now: datetime) -> bool:
    if not outputs_dir.is_dir():
        return False
    cutoff = now - timedelta(days=config.archive_after_days)
    found = False
    for path in iter_safe_paths(root, outputs_dir):
        if lstat_is_symlink(path):
            return False
        if not path.is_file():
            continue
        found = True
        if _mtime(path) > cutoff:
            return False
    return found


def _plan_old_outputs(root: Path, config: Config, now: datetime) -> list[PlannedAction]:
    actions: list[PlannedAction] = []
    sessions_root = root / "sessions"
    if not sessions_root.is_dir():
        return actions
    for session_dir in sorted(sessions_root.iterdir()):
        if not session_dir.is_dir():
            continue
        outputs_dir = session_dir / "outputs"
        if not outputs_fully_old(outputs_dir, root, config, now):
            continue
        archive_path = root / "archive" / f"{session_dir.name}.tar.gz"
        file_paths = [
            p
            for p in _collect_tree_paths(outputs_dir, root)
            if p.is_file() and not lstat_is_symlink(p)
        ]
        if not file_paths:
            continue
        total = sum(_file_size(p) for p in file_paths)
        actions.append(
            PlannedAction(
                kind=ActionKind.ARCHIVE,
                path=archive_path,
                bytes=total,
                detail=json.dumps([str(p.relative_to(root)) for p in file_paths]),
            )
        )
    return actions


def _plan_trash_purge(root: Path, config: Config, now: datetime) -> list[PlannedAction]:
    actions: list[PlannedAction] = []
    trash_root = root / ".trash"
    if not trash_root.is_dir():
        return actions
    cutoff_day = (now - timedelta(days=config.trash_ttl_days)).strftime("%Y-%m-%d")
    for day_dir in sorted(trash_root.iterdir()):
        if not day_dir.is_dir():
            continue
        if day_dir.name >= cutoff_day:
            continue
        for path in _collect_tree_paths(day_dir, root):
            actions.append(
                PlannedAction(
                    kind=ActionKind.PURGE,
                    path=path,
                    bytes=_file_size(path),
                    detail=f"trash day {day_dir.name}",
                )
            )
    return actions


def plan_run(root: Path, config: Config, now: datetime) -> list[PlannedAction]:
    actions: list[PlannedAction] = []
    actions.extend(_plan_manifest_discards(root, now))
    actions.extend(_plan_stale_scratch(root, config, now))
    actions.extend(_plan_old_outputs(root, config, now))
    actions.extend(_plan_trash_purge(root, config, now))
    return actions


def iter_session_dirs(root: Path) -> Iterator[Path]:
    sessions_root = root / "sessions"
    if not sessions_root.is_dir():
        return
    for child in sorted(sessions_root.iterdir()):
        if child.is_dir():
            yield child


def ambiguous_paths(root: Path) -> list[Path]:
    """Session-root files/dirs that are not known layout entries."""
    allowed_names = {"tmp", "outputs", "manifest.jsonl", ".session.json"}
    found: list[Path] = []
    for session_dir in iter_session_dirs(root):
        for child in session_dir.iterdir():
            if child.name in allowed_names:
                continue
            if lstat_is_symlink(child):
                found.append(child)
                continue
            try:
                realpath_inside_root(root, child)
            except Exception:
                continue
            found.append(child)
    return found
