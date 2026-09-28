"""session commands."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime

from slopsweep.config import load_config
from slopsweep.safety import EXIT_REFUSED, SafetyError, validate_root


def _session_id(explicit: str | None) -> str:
    return explicit if explicit else uuid.uuid4().hex[:12]


def cmd_session(args: argparse.Namespace) -> int:
    cfg = load_config(args.root)
    try:
        validated = validate_root(cfg.root)
    except SafetyError as exc:
        print(exc.message, flush=True)
        return EXIT_REFUSED
    root = validated.path
    session_id = _session_id(args.session_id)
    session_dir = root / "sessions" / session_id
    if args.session_cmd == "new":
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
        if not session_id:
            print("session id required", flush=True)
            return 2
        meta_file = session_dir / ".session.json"
        if not meta_file.is_file():
            print("session not found", flush=True)
            return 1
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        meta["ended_at"] = datetime.now(UTC).isoformat()
        meta_file.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(f"ended session {session_id}", flush=True)
        return 0
    return 2
