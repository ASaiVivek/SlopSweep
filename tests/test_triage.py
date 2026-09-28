from __future__ import annotations

import json
from pathlib import Path

import pytest

from slopsweep.config import Config
from slopsweep.triage import (
    build_triage_entry,
    matches_secret_pattern,
    parse_labels_file,
    validate_labels_file,
)


def test_secret_pattern_no_peek(workspace: Path) -> None:
    assert matches_secret_pattern(Path(".env.local"))
    sess = workspace / "sessions" / "s"
    sess.mkdir(parents=True)
    secret = sess / ".env"
    secret.write_text("KEY=supersecret\n", encoding="utf-8")
    cfg = Config(root=workspace)
    entry = build_triage_entry(workspace, secret, cfg)
    assert entry.peek == ""


def test_labels_validation_rejects_bad_label(workspace: Path) -> None:
    f = workspace / "sessions" / "s" / "x.txt"
    f.parent.mkdir(parents=True)
    f.write_text("a", encoding="utf-8")
    text = json.dumps({"path": "sessions/s/x.txt", "label": "destroy"}) + "\n"
    with pytest.raises(ValueError):
        parse_labels_file(text)


def test_labels_outside_root_rejected(workspace: Path) -> None:
    text = json.dumps({"path": "../outside.txt", "label": "delete"}) + "\n"
    with pytest.raises(ValueError):
        validate_labels_file(workspace, text)


def test_malformed_jsonl_rejects_whole_file(workspace: Path) -> None:
    text = "not json\n"
    with pytest.raises(ValueError):
        validate_labels_file(workspace, text)


def test_git_tracked_label_rejected(workspace: Path) -> None:
    repo = workspace / "sessions" / "s" / "proj"
    repo.mkdir(parents=True)
    (repo / ".git").mkdir()
    tracked = repo / "tracked.txt"
    tracked.write_text("x", encoding="utf-8")
    text = json.dumps({"path": "sessions/s/proj/tracked.txt", "label": "delete"}) + "\n"
    with pytest.raises(ValueError, match="git"):
        validate_labels_file(workspace, text)


def test_labels_whole_file_rejected_on_second_bad_line(workspace: Path) -> None:
    good = workspace / "sessions" / "s" / "ok.txt"
    good.parent.mkdir(parents=True)
    good.write_text("a", encoding="utf-8")
    line1 = json.dumps({"path": "sessions/s/ok.txt", "label": "keep"})
    line2 = json.dumps({"path": "sessions/s/ok.txt", "label": "nope"})
    with pytest.raises(ValueError):
        validate_labels_file(workspace, line1 + "\n" + line2 + "\n")


def test_symlink_label_rejected(workspace: Path) -> None:
    target = workspace / "sessions" / "s" / "real.txt"
    target.parent.mkdir(parents=True)
    target.write_text("x", encoding="utf-8")
    link = workspace / "sessions" / "s" / "link"
    link.symlink_to(target)
    rel = "sessions/s/link"
    text = json.dumps({"path": rel, "label": "delete"}) + "\n"
    with pytest.raises(ValueError):
        validate_labels_file(workspace, text)
