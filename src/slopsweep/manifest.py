"""Session manifest read/write."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

Verdict = Literal["keep", "discard"]


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    purpose: str
    verdict: Verdict
    ts: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "path": self.path,
                "purpose": self.purpose,
                "verdict": self.verdict,
                "ts": self.ts,
            },
            ensure_ascii=False,
        )


def manifest_path_for_session(root: Path, session_id: str) -> Path:
    return root / "sessions" / session_id / "manifest.jsonl"


def append_manifest_entry(
    manifest_file: Path,
    entry: ManifestEntry,
    *,
    now: datetime | None = None,
) -> None:
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    if now is None:
        now = datetime.now(UTC)
    if not entry.ts:
        entry = ManifestEntry(
            path=entry.path,
            purpose=entry.purpose,
            verdict=entry.verdict,
            ts=now.isoformat(),
        )
    line = entry.to_json() + "\n"
    fd, tmp_name = tempfile.mkstemp(dir=manifest_file.parent, prefix=".manifest-", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_fh:
            if manifest_file.is_file():
                tmp_fh.write(manifest_file.read_text(encoding="utf-8"))
            tmp_fh.write(line)
        os.replace(tmp_name, manifest_file)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def parse_manifest_lines(text: str) -> list[ManifestEntry]:
    entries: list[ManifestEntry] = []
    for lineno, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed manifest line {lineno}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"malformed manifest line {lineno}")
        path = data.get("path")
        purpose = data.get("purpose")
        verdict = data.get("verdict")
        ts = data.get("ts", "")
        if not isinstance(path, str) or not isinstance(purpose, str):
            raise ValueError(f"malformed manifest line {lineno}")
        if verdict not in ("keep", "discard"):
            raise ValueError(f"malformed manifest line {lineno}")
        entries.append(
            ManifestEntry(path=path, purpose=purpose, verdict=verdict, ts=str(ts))
        )
    return entries


def load_manifest(manifest_file: Path) -> list[ManifestEntry]:
    if not manifest_file.is_file():
        return []
    return parse_manifest_lines(manifest_file.read_text(encoding="utf-8"))
