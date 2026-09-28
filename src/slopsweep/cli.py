"""Command-line interface for slopsweep."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from slopsweep import TOOL_NAME, __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=TOOL_NAME, description="Agent workspace hygiene")
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="Create layout and marker file")
    init_p.add_argument("--root", type=Path, default=None, help="Workspace root")

    session_p = sub.add_parser("session", help="Session lifecycle")
    session_sub = session_p.add_subparsers(dest="session_cmd", required=True)
    new_p = session_sub.add_parser("new", help="Start a new session")
    new_p.add_argument("--id", dest="session_id", default=None)
    new_p.add_argument("--root", type=Path, default=None)
    end_p = session_sub.add_parser("end", help="End a session")
    end_p.add_argument("--id", dest="session_id", default=None)
    end_p.add_argument("--root", type=Path, default=None)

    manifest_p = sub.add_parser("manifest", help="Session manifest")
    manifest_sub = manifest_p.add_subparsers(dest="manifest_cmd", required=True)
    add_p = manifest_sub.add_parser("add", help="Append manifest entry")
    add_p.add_argument("path", type=Path)
    add_p.add_argument("--purpose", required=True)
    add_p.add_argument("--verdict", choices=["keep", "discard"], required=True)
    add_p.add_argument("--root", type=Path, default=None)
    add_p.add_argument("--session-id", default=None)

    run_p = sub.add_parser("run", help="Run cleanup phases (dry-run by default)")
    run_p.add_argument("--apply", action="store_true", help="Apply planned actions")
    run_p.add_argument("--json", action="store_true", help="JSON plan output")
    run_p.add_argument("--root", type=Path, default=None)

    triage_p = sub.add_parser("triage", help="Write metadata JSONL for ambiguous entries")
    triage_p.add_argument("--out", type=Path, default=None)
    triage_p.add_argument("--root", type=Path, default=None)

    labels_p = sub.add_parser("apply-labels", help="Validate and apply LLM labels")
    labels_p.add_argument("file", type=Path)
    labels_p.add_argument("--apply", action="store_true")
    labels_p.add_argument("--root", type=Path, default=None)

    sub.add_parser("status", help="Show workspace sizes").add_argument(
        "--root", type=Path, default=None
    )

    sub.add_parser("rules", help="Print agent rules block")

    hooks_p = sub.add_parser("hooks", help="Print integration snippets")
    hooks_sub = hooks_p.add_subparsers(dest="hooks_cmd", required=True)
    print_p = hooks_sub.add_parser("print", help="Print hook/cron snippets")
    print_p.add_argument(
        "--for",
        dest="target",
        choices=["claude-code", "codex", "cron"],
        required=True,
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "init":
        from slopsweep.commands_init import cmd_init

        return cmd_init(args)
    if args.command == "session":
        from slopsweep.commands_session import cmd_session

        return cmd_session(args)
    if args.command == "manifest":
        from slopsweep.commands_manifest import cmd_manifest

        return cmd_manifest(args)
    if args.command == "run":
        from slopsweep.commands_run import cmd_run

        return cmd_run(args)
    if args.command == "triage":
        from slopsweep.commands_triage import cmd_triage

        return cmd_triage(args)
    if args.command == "apply-labels":
        from slopsweep.commands_triage import cmd_apply_labels

        return cmd_apply_labels(args)
    if args.command == "status":
        from slopsweep.commands_run import cmd_status

        return cmd_status(args)
    if args.command == "rules":
        from slopsweep.commands_adapters import cmd_rules

        return cmd_rules()
    if args.command == "hooks":
        from slopsweep.commands_adapters import cmd_hooks_print

        return cmd_hooks_print(args)
    parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
