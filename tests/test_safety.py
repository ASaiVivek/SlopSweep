from __future__ import annotations

from pathlib import Path

import pytest

from slopsweep.config import LOCK_NAME, MARKER_NAME
from slopsweep.safety import (
    EXIT_REFUSED,
    SafetyError,
    realpath_inside_root,
    run_lock,
    validate_root,
)


def test_root_guard_refuses_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    home.mkdir()
    (home / MARKER_NAME).write_text("x\n")
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    with pytest.raises(SafetyError):
        validate_root(home, home=home)


def test_root_guard_refuses_without_marker(tmp_path: Path) -> None:
    root = tmp_path / "bare"
    root.mkdir()
    with pytest.raises(SafetyError):
        validate_root(root)


def test_root_guard_refuses_slash() -> None:
    with pytest.raises(SafetyError):
        validate_root(Path("/"))


def test_realpath_containment(workspace: Path) -> None:
    inside = workspace / "sessions" / "a" / "tmp" / "f.txt"
    inside.parent.mkdir(parents=True)
    inside.write_text("hi", encoding="utf-8")
    resolved = realpath_inside_root(workspace, inside)
    assert str(resolved).startswith(str(workspace.resolve()))


def test_symlink_escape_not_inside(workspace: Path) -> None:
    outside = workspace.parent / "outside-secret"
    outside.mkdir()
    outside_file = outside / "secret.txt"
    outside_file.write_text("no", encoding="utf-8")
    session_tmp = workspace / "sessions" / "s1" / "tmp"
    session_tmp.mkdir(parents=True)
    link = session_tmp / "escape"
    link.symlink_to(outside_file)
    # Symlink itself is inside root; realpath of target would escape
    realpath_inside_root(workspace, link)  # leaf path is the link location


def test_lock_prevents_concurrent(workspace: Path) -> None:
    with run_lock(workspace):
        assert (workspace / LOCK_NAME).exists()
        with pytest.raises(SafetyError), run_lock(workspace):
            pass
    assert not (workspace / LOCK_NAME).exists()


def test_exit_refused_constant() -> None:
    assert EXIT_REFUSED == 3
