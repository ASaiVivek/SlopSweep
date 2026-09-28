"""manifest commands."""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

from slopsweep.config import load_config
from slopsweep.manifest import ManifestEntry, append_manifest_entry, manifest_path_for_session
from slopsweep.safety import EXIT_REFUSED, SafetyError, realpath_inside_root, validate_root


def cmd_manifest(args: argparse.Namespace) -> int:
    cfg = load_config(args.root)
    try:
        validated = validate_root(cfg.root)
    except SafetyError as exc:
        print(exc.message, flush=True)
        return EXIT_REFUSED
    root = validated.path
    session_id = args.session_id or os.environ.get("SLOPSWEEP_SESSION")
    if not session_id:
        print("SLOPSWEEP_SESSION or --session-id required", flush=True)
        return 2
    if args.manifest_cmd != "add":
        return 2
    target = Path(args.path)
    try:
        if target.is_absolute():
            real = realpath_inside_root(root, target)
            rel = real.relative_to(root / "sessions" / session_id)
        else:
            real = realpath_inside_root(root, root / "sessions" / session_id / target)
            rel = real.relative_to(root / "sessions" / session_id)
    except SafetyError as exc:
        print(exc.message, flush=True)
        return EXIT_REFUSED
    entry = ManifestEntry(
        path=rel.as_posix(),
        purpose=args.purpose,
        verdict=args.verdict,
        ts=datetime.now(UTC).isoformat(),
    )
    append_manifest_entry(manifest_path_for_session(root, session_id), entry)
    print(f"manifest: {rel.as_posix()} -> {args.verdict}", flush=True)
    return 0
