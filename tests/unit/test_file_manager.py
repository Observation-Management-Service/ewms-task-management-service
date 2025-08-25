"""Test file_manager.py"""

import os
import tarfile
from pathlib import Path

import pytest

import tms.file_manager.file_manager as fm


# ---------- helpers ----------


def _touch(p: Path, content: str = "data") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def _make_old(p: Path, seconds_old: int) -> None:
    # Make file appear older by bumping mtime into the past
    now = int(os.path.getmtime(p))  # anchor on current fs time
    os.utime(p, (now - seconds_old, now - seconds_old))


# ---------- tests ----------


def test_000_rm_removes_file_and_logs(tmp_path, caplog):
    f = tmp_path / "a.txt"
    _touch(f)
    act = fm.FilepathAction("rm", age_threshold=0)
    assert f.exists()
    act._rm(f)
    assert not f.exists()
    assert any("done: rm" in rec.message for rec in caplog.records)


def test_010_mv_moves_file_and_makes_dest(tmp_path, caplog):
    src = tmp_path / "src" / "a.txt"
    dest_dir = tmp_path / "dest"
    _touch(src)
    act = fm.FilepathAction("mv", age_threshold=0, dest=dest_dir)
    act._mv(src)
    assert not src.exists()
    assert (dest_dir / "a.txt").exists()
    assert any("done: mv" in rec.message for rec in caplog.records)


def test_020_tar_creates_tar_gz_and_removes_source(tmp_path, caplog):
    # Use .tar.gz branch
    src = tmp_path / "file.log"
    _touch(src, "payload")
    tar_path = tmp_path / "archives" / "data.tar.gz"
    act = fm.FilepathAction("tar", age_threshold=0, dest=tar_path)

    act._tar(src)

    # source removed
    assert not src.exists()
    # tar created and contains our file
    assert tar_path.exists()
    with tarfile.open(tar_path, "r:gz") as tf:
        names = tf.getnames()
        assert "file.log" in names
        member = tf.getmember("file.log")
        fobj = tf.extractfile(member)
        assert fobj is not None and fobj.read().decode() == "payload"
    assert any("done: tar" in rec.message for rec in caplog.records)


def test_030_post_init_raises_if_dest_exists(tmp_path):
    # If a dest path already exists, __post_init__ should raise
    existing = tmp_path / "already_here"
    existing.mkdir(parents=True)
    with pytest.raises(RuntimeError, match="destination already exists"):
        fm.FilepathAction("mv", age_threshold=0, dest=existing)


def test_1000_is_old_enough_true_and_false(tmp_path):
    f = tmp_path / "x.bin"
    _touch(f)

    act = fm.FilepathAction("rm", age_threshold=10)

    # Not old enough initially
    assert not act.is_old_enough(f)

    # Make old enough
    _make_old(f, seconds_old=60)
    assert act.is_old_enough(f)


def test_1100_act_no_action_when_not_old_enough(tmp_path, caplog, monkeypatch):
    f = tmp_path / "file.txt"
    _touch(f)
    # Age threshold 1 day; file is brand new
    act = fm.FilepathAction("rm", age_threshold=24 * 3600)

    act.act(f)

    # File remains
    assert f.exists()
    # Log line shows "no action"
    assert any(
        "no action -- filepath not older" in rec.message for rec in caplog.records
    )


def test_1200_act_unknown_action_raises_valueerror(tmp_path):
    f = tmp_path / "file.txt"
    _touch(f)

    # Create an instance with an invalid action token
    bad = fm.FilepathAction("nope", age_threshold=0)
    with pytest.raises(ValueError, match="Unknown action"):
        bad.act(f)
