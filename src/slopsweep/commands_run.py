"""run and status commands."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from slopsweep.config import load_config
from slopsweep.execute import execute_plan
from slopsweep.plan import ActionKind, plan_run
from slopsweep.safety import EXIT_REFUSED, SafetyError, run_lock, validate_root


def cmd_run(args: argparse.Namespace) -> int:
    cfg = load_config(args.root)
    try:
        validated = validate_root(cfg.root)
    except SafetyError as exc:
        print(exc.message, flush=True)
        return EXIT_REFUSED
    root = validated.path
    now = datetime.now(UTC)
    dry_run = not args.apply
    try:
        with run_lock(root):
            actions = plan_run(root, cfg, now)
            if args.json:
                payload = [
                    {
                        "kind": a.kind.value,
                        "path": str(a.path),
                        "bytes": a.bytes,
                        "detail": a.detail,
                    }
                    for a in actions
                ]
                print(json.dumps(payload, indent=2), flush=True)
            else:
                mode = "dry-run" if dry_run else "apply"
                print(f"slopsweep run ({mode}): {len(actions)} action(s)", flush=True)
                for action in actions:
                    print(f"  {action.kind.value}: {action.path} ({action.bytes} B)", flush=True)
            execute_plan(root, actions, dry_run=dry_run, now=now)
    except SafetyError as exc:
        print(exc.message, flush=True)
        return EXIT_REFUSED
    return 0


def _dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for root, _dirs, files in os_walk_safe(path):
        for name in files:
            fp = Path(root) / name
            try:
                total += fp.lstat().st_size
            except OSError:
                pass
    return total


def os_walk_safe(
    path: Path,
) -> Iterator[tuple[str, list[str], list[str]]]:
    for dirpath, dirnames, filenames in os.walk(path, topdown=True, followlinks=False):
        dirnames[:] = [d for d in dirnames if not (Path(dirpath) / d).is_symlink()]
        yield dirpath, dirnames, filenames


def cmd_status(args: argparse.Namespace) -> int:

    cfg = load_config(args.root)
    try:
        validated = validate_root(cfg.root)
    except SafetyError as exc:
        print(exc.message, flush=True)
        return EXIT_REFUSED
    root = validated.path
    now = datetime.now(UTC)
    planned = plan_run(root, cfg, now)
    reclaimable = sum(a.bytes for a in planned if a.kind in (ActionKind.TRASH, ActionKind.PURGE))
    sessions_root = root / "sessions"
    print(f"root: {root}", flush=True)
    if sessions_root.is_dir():
        for session_dir in sorted(sessions_root.iterdir()):
            if session_dir.is_dir():
                size = _dir_size(session_dir)
                print(f"  session {session_dir.name}: {size} B", flush=True)
    trash_size = _dir_size(root / ".trash")
    archive_size = _dir_size(root / "archive")
    print(f"trash: {trash_size} B", flush=True)
    print(f"archive: {archive_size} B", flush=True)
    print(f"estimated reclaimable (planned trash/purge): {reclaimable} B", flush=True)
    return 0
