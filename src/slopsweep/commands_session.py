"""session commands."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import UTC, datetime

from slopsweep.config import load_config
from slopsweep.safety import EXIT_REFUSED, SafetyError, validate_root


def _session_id_for_new(explicit: str | None) -> str:
    return explicit if explicit else uuid.uuid4().hex[:12]


def _session_id_for_end(explicit: str | None) -> str | None:
    if explicit:
        return explicit
    env_id = os.environ.get("SLOPSWEEP_SESSION")
    return env_id if env_id else None


def cmd_session(args: argparse.Namespace) -> int:
    cfg = load_config(args.root)
    try:
        validated = validate_root(cfg.root)
    except SafetyError as exc:
        print(exc.message, flush=True)
        return EXIT_REFUSED
    root = validated.path
    if args.session_cmd == "new":
        session_id = _session_id_for_new(args.session_id)
        session_dir = root / "sessions" / session_id
        for sub in ("tmp", "outputs"):
            (session_dir / sub).mkdir(parents=True, exist_ok=True)
        meta = {
            "started_at": datetime.now(UTC).isoformat(),
            "ended_at": None,
        }
        (session_dir / ".session.json").write_text(
            json.dumps(meta, indent=2) + "\n",
            encoding="utf-8",
        )
        tmp = session_dir / "tmp"
        print(f"export SLOPSWEEP_ROOT={root}", flush=True)
        print(f"export SLOPSWEEP_SESSION={session_id}", flush=True)
        print(f"export TMPDIR={tmp}", flush=True)
        return 0
    if args.session_cmd == "end":
        end_session_id: str | None = _session_id_for_end(args.session_id)
        if end_session_id is None:
            print("SLOPSWEEP_SESSION or --id required", flush=True)
            return 2
        session_dir = root / "sessions" / end_session_id
        meta_file = session_dir / ".session.json"
        if not meta_file.is_file():
            print("session not found", flush=True)
            return 1
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        meta["ended_at"] = datetime.now(UTC).isoformat()
        meta_file.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(f"ended session {end_session_id}", flush=True)
        return 0
    return 2
