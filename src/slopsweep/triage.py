"""Metadata-only triage and label validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from slopsweep.config import Config
from slopsweep.safety import (
    is_git_tracked_or_in_work_tree,
    lstat_is_symlink,
    realpath_inside_root,
)

Label = Literal["keep", "archive", "delete"]

SECRET_PATTERNS = [
    re.compile(r"\.env", re.IGNORECASE),
    re.compile(r"\.pem$", re.IGNORECASE),
    re.compile(r"\.key$", re.IGNORECASE),
    re.compile(r"^id_rsa", re.IGNORECASE),
    re.compile(r"credentials", re.IGNORECASE),
    re.compile(r"\.p12$", re.IGNORECASE),
    re.compile(r"\.pfx$", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
]


def matches_secret_pattern(path: Path) -> bool:
    name = path.name
    return any(pattern.search(name) for pattern in SECRET_PATTERNS)


def _kind_for(path: Path) -> str:
    if lstat_is_symlink(path):
        return "symlink"
    if path.is_dir():
        return "dir"
    return "file"


def _peek_text(path: Path, max_bytes: int) -> str:
    if matches_secret_pattern(path):
        return ""
    if lstat_is_symlink(path) or path.is_dir():
        return ""
    try:
        with path.open("rb") as fh:
            data = fh.read(max_bytes)
    except OSError:
        return ""
    if b"\x00" in data:
        return ""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return ""


@dataclass(frozen=True)
class TriageEntry:
    path: str
    kind: str
    size_bytes: int
    mtime: float
    peek: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "path": self.path,
                "kind": self.kind,
                "size_bytes": self.size_bytes,
                "mtime": self.mtime,
                "peek": self.peek,
            },
            ensure_ascii=False,
        )


def build_triage_entry(root: Path, path: Path, config: Config) -> TriageEntry:
    rel = path.relative_to(root).as_posix()
    st = path.lstat()
    return TriageEntry(
        path=rel,
        kind=_kind_for(path),
        size_bytes=st.st_size,
        mtime=st.st_mtime,
        peek=_peek_text(path, config.triage_peek_bytes),
    )


@dataclass(frozen=True)
class LabelEntry:
    path: str
    label: Label


def parse_labels_file(text: str) -> list[LabelEntry]:
    entries: list[LabelEntry] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed labels file at line {lineno}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"malformed labels file at line {lineno}")
        path = data.get("path")
        label = data.get("label")
        if not isinstance(path, str) or label not in ("keep", "archive", "delete"):
            raise ValueError(f"malformed labels file at line {lineno}")
        entries.append(LabelEntry(path=path, label=label))
    return entries


def validate_label_entry(root: Path, entry: LabelEntry) -> Path:
    target = root / entry.path
    if not target.exists():
        raise ValueError(f"path does not exist: {entry.path}")
    if lstat_is_symlink(target):
        raise ValueError(f"refusing symlink: {entry.path}")
    realpath_inside_root(root, target)
    if is_git_tracked_or_in_work_tree(root, target):
        raise ValueError(f"refusing git path: {entry.path}")
    return target


def validate_labels_file(root: Path, text: str) -> list[tuple[LabelEntry, Path]]:
    """Parse and validate all labels; reject whole file on any error."""
    try:
        entries = parse_labels_file(text)
    except ValueError:
        raise
    resolved: list[tuple[LabelEntry, Path]] = []
    for entry in entries:
        resolved.append((entry, validate_label_entry(root, entry)))
    return resolved
