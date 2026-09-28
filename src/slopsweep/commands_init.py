"""init command."""

from __future__ import annotations

import argparse
from pathlib import Path

from slopsweep.config import CONFIG_DIR, CONFIG_FILE, MARKER_NAME, default_config_toml, load_config
from slopsweep.safety import is_filesystem_root


def cmd_init(args: argparse.Namespace) -> int:
    cfg = load_config(args.root)
    root = cfg.root
    if is_filesystem_root(root) or root == Path.home().resolve():
        print("refused: unsafe root", flush=True)
        return 3
    root.mkdir(parents=True, exist_ok=True)
    for name in ("sessions", ".trash", "archive", "logs"):
        (root / name).mkdir(parents=True, exist_ok=True)
    marker = root / MARKER_NAME
    marker.write_text("slopsweep workspace\n", encoding="utf-8")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.is_file():
        CONFIG_FILE.write_text(default_config_toml(), encoding="utf-8")
    print(f"initialized {root}", flush=True)
    return 0
