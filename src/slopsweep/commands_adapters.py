"""rules and hooks adapters."""

from __future__ import annotations

import argparse
from importlib import resources


def _read_packaged(name: str) -> str:
    data = resources.files("slopsweep").joinpath("data", name)
    return data.read_text(encoding="utf-8")


def cmd_rules() -> int:
    text = _read_packaged("AGENT_RULES.md")
    print(text, end="" if text.endswith("\n") else "\n", flush=True)
    return 0


def cmd_hooks_print(args: argparse.Namespace) -> int:
    target = args.target
    if target == "claude-code":
        snippet = _read_packaged("hooks-claude-code.json")
    elif target == "codex":
        snippet = _read_packaged("hooks-codex.md")
    else:
        snippet = _read_packaged("hooks-cron.txt")
    print(snippet, end="" if snippet.endswith("\n") else "\n", flush=True)
    return 0
