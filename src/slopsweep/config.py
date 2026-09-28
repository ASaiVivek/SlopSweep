"""Configuration loading and defaults."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from slopsweep import TOOL_NAME

DEFAULT_ROOT = Path.home() / "agent-work"
CONFIG_DIR = Path.home() / ".config" / TOOL_NAME
CONFIG_FILE = CONFIG_DIR / "config.toml"

MARKER_NAME = ".slopsweep-root"
LOCK_NAME = ".slopsweep.lock"


@dataclass(frozen=True)
class Config:
    root: Path
    scratch_ttl_hours: int = 24
    trash_ttl_days: int = 7
    archive_after_days: int = 30
    triage_peek_bytes: int = 200

    @staticmethod
    def default_root() -> Path:
        env = os.environ.get("SLOPSWEEP_ROOT")
        if env:
            return Path(env).expanduser()
        return DEFAULT_ROOT


def _read_toml(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        raw: dict[str, object] = tomllib.load(fh)
    return raw


def load_config(
    root: Path | None = None,
    *,
    scratch_ttl_hours: int | None = None,
    trash_ttl_days: int | None = None,
    archive_after_days: int | None = None,
    triage_peek_bytes: int | None = None,
) -> Config:
    file_data = _read_toml(CONFIG_FILE)
    section = file_data.get("defaults", file_data)
    if not isinstance(section, dict):
        section = {}

    def _int(key: str, default: int, override: int | None) -> int:
        if override is not None:
            return override
        env_key = f"SLOPSWEEP_{key.upper()}"
        if env_key in os.environ:
            return int(os.environ[env_key])
        val = section.get(key)
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(val)
        return default

    resolved_root = root if root is not None else Config.default_root()
    env_root = os.environ.get("SLOPSWEEP_ROOT")
    if root is None and env_root:
        resolved_root = Path(env_root).expanduser()

    return Config(
        root=resolved_root.expanduser().resolve(),
        scratch_ttl_hours=_int("scratch_ttl_hours", 24, scratch_ttl_hours),
        trash_ttl_days=_int("trash_ttl_days", 7, trash_ttl_days),
        archive_after_days=_int("archive_after_days", 30, archive_after_days),
        triage_peek_bytes=_int("triage_peek_bytes", 200, triage_peek_bytes),
    )


def default_config_toml() -> str:
    return """# slopsweep defaults — see docs/safety-model.md

[defaults]
scratch_ttl_hours = 24
trash_ttl_days = 7
archive_after_days = 30
triage_peek_bytes = 200
"""
