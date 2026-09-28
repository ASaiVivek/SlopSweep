"""Apply planned actions."""

from __future__ import annotations

import json
import os
import shutil
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from slopsweep.plan import ActionKind, PlannedAction
from slopsweep.safety import lstat_is_symlink


@dataclass(frozen=True)
class AuditRecord:
    timestamp: str
    action: str
    path: str
    bytes: int
    dry_run: bool
    detail: str = ""

    def to_jsonl(self) -> str:
        return json.dumps(
            {
                "timestamp": self.timestamp,
                "action": self.action,
                "path": self.path,
                "bytes": self.bytes,
                "dry_run": self.dry_run,
                "detail": self.detail,
            },
            ensure_ascii=False,
        )


def _utc_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _audit_log_path(root: Path) -> Path:
    return root / "logs" / "slopsweep.jsonl"


def append_audit(root: Path, record: AuditRecord) -> None:
    log_path = _audit_log_path(root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(record.to_jsonl() + "\n")


def _trash_dest(root: Path, source: Path, now: datetime, *, create_parents: bool) -> Path:
    day = _utc_now(now).strftime("%Y-%m-%d")
    rel = source.relative_to(root)
    dest = root / ".trash" / day / rel
    if create_parents:
        dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def move_to_trash(root: Path, source: Path, now: datetime, *, dry_run: bool) -> Path:
    dest = _trash_dest(root, source, now, create_parents=not dry_run)
    if dry_run:
        return dest
    if source.is_dir() and not lstat_is_symlink(source):
        if dest.exists():
            shutil.rmtree(dest)
        shutil.move(str(source), str(dest))
    else:
        if dest.exists():
            dest.unlink()
        shutil.move(str(source), str(dest))
    return dest


def verify_archive(archive_path: Path, expected_members: list[str]) -> None:
    with tarfile.open(archive_path, "r:gz") as tf:
        names = set(tf.getnames())
    for member in expected_members:
        if member not in names:
            raise OSError(f"missing member in archive: {member}")


def create_verified_archive(
    archive_path: Path,
    files: list[Path],
    root: Path,
    *,
    dry_run: bool,
) -> None:
    members = [str(f.relative_to(root).as_posix()) for f in files]
    if dry_run:
        return
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    partial = archive_path.with_suffix(archive_path.suffix + ".partial")
    try:
        with tarfile.open(partial, "w:gz") as tf:
            for file_path in files:
                arcname = file_path.relative_to(root).as_posix()
                if lstat_is_symlink(file_path):
                    continue
                tf.add(file_path, arcname=arcname, recursive=False)
        verify_archive(partial, members)
        os.replace(partial, archive_path)
        for file_path in files:
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir() and not lstat_is_symlink(file_path):
                shutil.rmtree(file_path)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def purge_path(path: Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    if path.is_dir() and not lstat_is_symlink(path):
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def execute_plan(
    root: Path,
    actions: list[PlannedAction],
    *,
    dry_run: bool,
    now: datetime | None = None,
) -> list[AuditRecord]:
    ts = _utc_now(now).isoformat()
    records: list[AuditRecord] = []
    for action in actions:
        if action.kind == ActionKind.TRASH:
            dest = move_to_trash(root, action.path, _utc_now(now), dry_run=dry_run)
            rec = AuditRecord(
                timestamp=ts,
                action=action.kind.value,
                path=str(action.path),
                bytes=action.bytes,
                dry_run=dry_run,
                detail=str(dest),
            )
            records.append(rec)
        elif action.kind == ActionKind.ARCHIVE:
            file_paths = json.loads(action.detail)
            paths = [root / p for p in file_paths]
            create_verified_archive(action.path, paths, root, dry_run=dry_run)
            rec = AuditRecord(
                timestamp=ts,
                action=action.kind.value,
                path=str(action.path),
                bytes=action.bytes,
                dry_run=dry_run,
                detail=action.detail,
            )
            records.append(rec)
        elif action.kind == ActionKind.PURGE:
            purge_path(action.path, dry_run=dry_run)
            rec = AuditRecord(
                timestamp=ts,
                action=action.kind.value,
                path=str(action.path),
                bytes=action.bytes,
                dry_run=dry_run,
                detail=action.detail,
            )
            records.append(rec)
    if not dry_run:
        for rec in records:
            append_audit(root, rec)
    return records
