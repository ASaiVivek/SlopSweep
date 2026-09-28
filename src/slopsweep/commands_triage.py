"""triage and apply-labels commands."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from slopsweep.config import load_config
from slopsweep.execute import create_verified_archive, move_to_trash
from slopsweep.plan import ambiguous_paths
from slopsweep.safety import EXIT_REFUSED, SafetyError, run_lock, validate_root
from slopsweep.triage import build_triage_entry, validate_labels_file


def cmd_triage(args: argparse.Namespace) -> int:
    cfg = load_config(args.root)
    try:
        validated = validate_root(cfg.root)
    except SafetyError as exc:
        print(exc.message, flush=True)
        return EXIT_REFUSED
    root = validated.path
    out_path = args.out if args.out is not None else root / "triage.jsonl"
    paths = ambiguous_paths(root)
    lines: list[str] = []
    for path in paths:
        lines.append(build_triage_entry(root, path, cfg).to_json())
    out_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(f"wrote {len(lines)} entries to {out_path}", flush=True)
    return 0


def cmd_apply_labels(args: argparse.Namespace) -> int:
    cfg = load_config(args.root)
    try:
        validated = validate_root(cfg.root)
    except SafetyError as exc:
        print(exc.message, flush=True)
        return EXIT_REFUSED
    root = validated.path
    text = args.file.read_text(encoding="utf-8")
    try:
        labeled = validate_labels_file(root, text)
    except ValueError as exc:
        print(str(exc), flush=True)
        return 1
    dry_run = not args.apply
    now = datetime.now(UTC)
    try:
        with run_lock(root):
            for entry, target in labeled:
                if entry.label == "keep":
                    print(f"keep: {entry.path}", flush=True)
                elif entry.label == "delete":
                    dest = move_to_trash(root, target, now, dry_run=dry_run)
                    print(f"delete -> trash: {entry.path} ({dest})", flush=True)
                elif entry.label == "archive":
                    safe_name = entry.path.replace("/", "_")
                    archive_path = root / "archive" / f"triage-{safe_name}.tar.gz"
                    files = [target] if target.is_file() else []
                    if target.is_dir():
                        import os

                        for dirpath, _dn, filenames in os.walk(target, followlinks=False):
                            for name in filenames:
                                fp = Path(dirpath) / name
                                if not fp.is_symlink():
                                    files.append(fp)
                    create_verified_archive(archive_path, files, root, dry_run=dry_run)
                    print(f"archive: {entry.path} -> {archive_path}", flush=True)
    except SafetyError as exc:
        print(exc.message, flush=True)
        return EXIT_REFUSED
    except OSError as exc:
        print(str(exc), flush=True)
        return 1
    return 0
