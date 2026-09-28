from __future__ import annotations

import json
import os
import shutil
import tarfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from slopsweep.config import Config
from slopsweep.execute import create_verified_archive, execute_plan
from slopsweep.manifest import ManifestEntry, append_manifest_entry, manifest_path_for_session
from slopsweep.plan import plan_run, scratch_eligible


def _session(workspace: Path, session_id: str = "sess1") -> Path:
    d = workspace / "sessions" / session_id
    (d / "tmp").mkdir(parents=True)
    (d / "outputs").mkdir()
    (d / ".session.json").write_text(
        json.dumps({"started_at": "t", "ended_at": None}),
        encoding="utf-8",
    )
    return d


def test_dry_run_changes_nothing(workspace: Path, frozen_now: datetime) -> None:
    sess = _session(workspace)
    scratch = sess / "tmp" / "old.txt"
    scratch.write_text("data", encoding="utf-8")
    os.utime(scratch, (0, 0))
    cfg = Config(root=workspace, scratch_ttl_hours=24)
    before = shutil.disk_usage(workspace).used
    tree_before = list(workspace.rglob("*"))
    actions = plan_run(workspace, cfg, frozen_now)
    execute_plan(workspace, actions, dry_run=True, now=frozen_now)
    tree_after = list(workspace.rglob("*"))
    assert sorted(tree_before) == sorted(tree_after)
    assert scratch.exists()
    assert before == shutil.disk_usage(workspace).used


def test_scratch_ttl_boundary(workspace: Path, frozen_now: datetime) -> None:
    sess = _session(workspace)
    recent = sess / "tmp" / "new.txt"
    recent.write_text("x", encoding="utf-8")
    cfg = Config(root=workspace, scratch_ttl_hours=24)
    assert scratch_eligible(sess, workspace, cfg, frozen_now) is False


def test_ended_session_scratch_eligible(workspace: Path, frozen_now: datetime) -> None:
    sess = _session(workspace)
    meta = json.loads((sess / ".session.json").read_text(encoding="utf-8"))
    meta["ended_at"] = frozen_now.isoformat()
    (sess / ".session.json").write_text(json.dumps(meta), encoding="utf-8")
    recent = sess / "tmp" / "new.txt"
    recent.write_text("x", encoding="utf-8")
    cfg = Config(root=workspace, scratch_ttl_hours=24)
    assert scratch_eligible(sess, workspace, cfg, frozen_now) is True


def test_manifest_discard(workspace: Path, frozen_now: datetime) -> None:
    sess = _session(workspace)
    stray = sess / "stray.txt"
    stray.write_text("bye", encoding="utf-8")
    append_manifest_entry(
        manifest_path_for_session(workspace, "sess1"),
        ManifestEntry(path="stray.txt", purpose="test", verdict="discard", ts="t"),
    )
    cfg = Config(root=workspace)
    actions = plan_run(workspace, cfg, frozen_now)
    kinds = [a.path.name for a in actions if a.path.name == "stray.txt"]
    assert kinds == ["stray.txt"]
    execute_plan(workspace, actions, dry_run=False, now=frozen_now)
    assert not stray.exists()
    trash_files = list((workspace / ".trash").rglob("stray.txt"))
    assert trash_files


def test_archive_verify_failure_keeps_originals(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sess = _session(workspace)
    out = sess / "outputs" / "deliverable.txt"
    out.write_text("important", encoding="utf-8")
    old = datetime(2020, 1, 1, tzinfo=UTC).timestamp()
    os.utime(out, (old, old))
    archive_path = workspace / "archive" / "sess1.tar.gz"

    def boom(_archive: Path, _members: list[str]) -> None:
        raise OSError("verify failed")

    monkeypatch.setattr("slopsweep.execute.verify_archive", boom)
    with pytest.raises(OSError):
        create_verified_archive(archive_path, [out], workspace, dry_run=False)
    assert out.exists()
    assert not archive_path.exists()


def test_symlink_in_tmp_not_deleted_through(workspace: Path, frozen_now: datetime) -> None:
    outside = workspace.parent / "victim.txt"
    outside.write_text("keep", encoding="utf-8")
    sess = _session(workspace)
    meta = json.loads((sess / ".session.json").read_text(encoding="utf-8"))
    meta["ended_at"] = frozen_now.isoformat()
    (sess / ".session.json").write_text(json.dumps(meta), encoding="utf-8")
    link = sess / "tmp" / "link"
    link.symlink_to(outside)
    cfg = Config(root=workspace)
    actions = plan_run(workspace, cfg, frozen_now)
    execute_plan(workspace, actions, dry_run=False, now=frozen_now)
    assert outside.read_text(encoding="utf-8") == "keep"


def test_git_work_tree_skipped(workspace: Path, frozen_now: datetime) -> None:
    sess = _session(workspace)
    repo = sess / "tmp" / "project"
    repo.mkdir()
    (repo / ".git").mkdir()
    tracked = repo / "file.txt"
    tracked.write_text("x", encoding="utf-8")
    meta = json.loads((sess / ".session.json").read_text(encoding="utf-8"))
    meta["ended_at"] = frozen_now.isoformat()
    (sess / ".session.json").write_text(json.dumps(meta), encoding="utf-8")
    cfg = Config(root=workspace)
    actions = plan_run(workspace, cfg, frozen_now)
    assert tracked not in [a.path for a in actions]


def test_unicode_and_space_filenames(workspace: Path, frozen_now: datetime) -> None:
    sess = _session(workspace)
    name = "file with spaces 🚀.txt"
    path = sess / "tmp" / name
    path.write_text("x", encoding="utf-8")
    meta = json.loads((sess / ".session.json").read_text(encoding="utf-8"))
    meta["ended_at"] = frozen_now.isoformat()
    (sess / ".session.json").write_text(json.dumps(meta), encoding="utf-8")
    cfg = Config(root=workspace)
    actions = plan_run(workspace, cfg, frozen_now)
    assert any(a.path.name == name for a in actions)


def test_trash_purge_boundary(workspace: Path, frozen_now: datetime) -> None:
    old_day = (frozen_now - timedelta(days=10)).strftime("%Y-%m-%d")
    trash_file = workspace / ".trash" / old_day / "gone.txt"
    trash_file.parent.mkdir(parents=True)
    trash_file.write_text("x", encoding="utf-8")
    cfg = Config(root=workspace, trash_ttl_days=7)
    actions = plan_run(workspace, cfg, frozen_now)
    assert any(a.path == trash_file for a in actions)
    execute_plan(workspace, actions, dry_run=False, now=frozen_now)
    assert not trash_file.exists()


def test_old_outputs_archived(workspace: Path, frozen_now: datetime) -> None:
    sess = _session(workspace)
    out = sess / "outputs" / "old.txt"
    out.write_text("data", encoding="utf-8")
    old = (frozen_now - timedelta(days=60)).timestamp()
    os.utime(out, (old, old))
    cfg = Config(root=workspace, archive_after_days=30)
    actions = plan_run(workspace, cfg, frozen_now)
    archive_actions = [a for a in actions if a.path.suffix == ".gz"]
    assert archive_actions
    execute_plan(workspace, actions, dry_run=False, now=frozen_now)
    archive = workspace / "archive" / "sess1.tar.gz"
    assert archive.exists()
    with tarfile.open(archive, "r:gz") as tf:
        assert "sessions/sess1/outputs/old.txt" in tf.getnames()
    assert not out.exists()
