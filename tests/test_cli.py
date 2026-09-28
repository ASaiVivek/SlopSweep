from __future__ import annotations

import json
from pathlib import Path

import pytest

from slopsweep.cli import main


def test_cli_help() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_init_and_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "agent"
    monkeypatch.delenv("SLOPSWEEP_ROOT", raising=False)
    assert main(["init", "--root", str(root)]) == 0
    assert (root / ".slopsweep-root").is_file()
    monkeypatch.setenv("SLOPSWEEP_ROOT", str(root))
    assert main(["session", "new", "--id", "demo"]) == 0
    assert (root / "sessions" / "demo" / "tmp").is_dir()
    monkeypatch.setenv("SLOPSWEEP_SESSION", "demo")
    assert main(["session", "end"]) == 0
    meta = json.loads(
        (root / "sessions" / "demo" / ".session.json").read_text(encoding="utf-8")
    )
    assert meta["ended_at"] is not None
