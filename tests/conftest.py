from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from slopsweep.config import MARKER_NAME, load_config


@pytest.fixture
def frozen_now() -> datetime:
    return datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    (root / MARKER_NAME).write_text("ok\n", encoding="utf-8")
    for name in ("sessions", ".trash", "archive", "logs"):
        (root / name).mkdir()
    monkeypatch.setenv("SLOPSWEEP_ROOT", str(root))
    return root


@pytest.fixture
def config(workspace: Path):
    return load_config(workspace)
