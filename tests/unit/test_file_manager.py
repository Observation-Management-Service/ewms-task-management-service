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
    assert f.exists()

    fm.action_rm(f)

    assert not f.exists()
    assert any("done: rm" in rec.message for rec in caplog.records)


def test_010_mv_moves_file_and_makes_dest(tmp_path, caplog):
    src = tmp_path / "src" / "a.txt"
    dest_dir = tmp_path / "dest"
    _touch(src)

    dest_dir.mkdir()  # bash requires the directory to already exist

    fm.action_mv(src, dest=dest_dir)

    assert not src.exists()
    assert (dest_dir / "a.txt").exists()
    assert any("done: mv" in rec.message for rec in caplog.records)


def test_011_mv_renames_when_dest_missing_parent_exists(tmp_path, caplog):
    src = tmp_path / "src" / "a.txt"
    _touch(src)

    # dest does not exist -> treated as rename; parent DOES exist
    parent = tmp_path / "newdir"
    parent.mkdir()
    final = parent / "renamed.txt"

    fm.action_mv(src, dest=final)

    assert not src.exists()
    assert final.exists()
    assert any("done: mv" in rec.message for rec in caplog.records)


def test_012_mv_rename_errors_if_parent_missing(tmp_path):
    src = tmp_path / "src" / "a.txt"
    _touch(src)

    # parent of dest missing -> bash mv errors; so do we
    final = tmp_path / "newdir" / "renamed.txt"

    with pytest.raises(FileNotFoundError):
        fm.action_mv(src, dest=final)


def test_013_mv_overwrites_existing_file_like_bash(tmp_path, caplog):
    src = tmp_path / "a.txt"
    dst = tmp_path / "b.txt"
    _touch(src, "new")
    _touch(dst, "old")

    fm.action_mv(src, dest=dst)

    assert not src.exists()
    assert dst.read_text() == "new"
    assert any("done: mv" in rec.message for rec in caplog.records)


def test_020_tar_gz_creates_archive_and_removes_source(tmp_path, caplog):
    # Source is a directory; archive should land in dest directory
    src_dir = tmp_path / "srcdir"
    file_inside = src_dir / "file.log"
    _touch(file_inside, "payload")

    dest_dir = tmp_path / "archives"
    fm.action_tar_gz(src_dir, dest=dest_dir)

    # source removed
    assert not src_dir.exists()
    # tar created and contains our file under the preserved top-level directory
    tar_path = dest_dir / "srcdir.tar.gz"
    assert tar_path.exists()
    with tarfile.open(tar_path, "r:gz") as tf:
        names = tf.getnames()
        assert "srcdir/file.log" in names
        member = tf.getmember("srcdir/file.log")
        fobj = tf.extractfile(member)
        assert fobj is not None and fobj.read().decode() == "payload"
    assert any("done: tar.gz" in rec.message for rec in caplog.records)


def test_021_mv_raises_if_no_dest(tmp_path):
    f = tmp_path / "file.txt"
    _touch(f)
    # Pass dest=None so we exercise our RuntimeError (not a Python TypeError)
    with pytest.raises(RuntimeError, match="destination not given"):
        fm.action_mv(f, dest=None)  # type: ignore[arg-type]


def test_022_tar_gz_raises_if_no_dest(tmp_path):
    src_dir = tmp_path / "srcdir"
    (src_dir / "file.txt").parent.mkdir(parents=True)
    _touch(src_dir / "file.txt")

    with pytest.raises(RuntimeError, match="destination not given"):
        fm.action_tar_gz(src_dir, dest=None)  # type: ignore[arg-type]


def test_023_tar_gz_raises_if_src_not_dir(tmp_path):
    f = tmp_path / "file.txt"
    _touch(f)
    dest = tmp_path / "out"
    dest.mkdir()

    with pytest.raises(NotADirectoryError):
        fm.action_tar_gz(f, dest=dest)


async def test_024_act_skips_if_precheck_fails(tmp_path, caplog):
    f = tmp_path / "f.txt"
    _touch(f)

    async def bad_precheck(_):
        return False

    act = fm.FileManager(
        fpattern="*", action=fm.action_rm, age_threshold=0, precheck_async=bad_precheck
    )

    await act.act(f)

    # File remains, log mentions precheck
    assert f.exists()
    assert any("precheck returned 'False' for" in rec.message for rec in caplog.records)


async def test_025_act_raises_if_missing(tmp_path):
    f = tmp_path / "does_not_exist"
    act = fm.FileManager(fpattern="*", action=fm.action_rm, age_threshold=0)
    with pytest.raises(FileNotFoundError):
        await act.act(f)


def test_1000_is_old_enough_true_and_false(tmp_path):
    f = tmp_path / "x.bin"
    _touch(f)

    act = fm.FileManager(fpattern="*", action=fm.action_rm, age_threshold=10)

    # Not old enough initially
    assert not act.is_old_enough(f)

    # Make old enough
    _make_old(f, seconds_old=60)
    assert act.is_old_enough(f)


def test_1010_is_old_enough_dir_uses_latest_child_mtime(tmp_path):
    """Dir should be 'young' if any child is young; 'old' only when all children are old."""
    d = tmp_path / "dir"
    (d / "sub").mkdir(parents=True)
    old_f = d / "old.txt"
    young_f = d / "sub" / "young.txt"
    _touch(old_f)
    _touch(young_f)

    act = fm.FileManager(fpattern="*", action=fm.action_rm, age_threshold=10)

    # Make the directory itself appear old, and one child old...
    _make_old(d, seconds_old=60)
    _make_old(old_f, seconds_old=60)

    # ...but a different child is still fresh → NOT old enough
    assert not act.is_old_enough(d)

    # Now make the young child old too → NOW old enough
    _make_old(young_f, seconds_old=60)
    assert act.is_old_enough(d)


def test_1020_is_old_enough_empty_dir_uses_itself(tmp_path):
    """Empty directory should fall back to its own mtime."""
    d = tmp_path / "emptydir"
    d.mkdir()

    act = fm.FileManager(fpattern="*", action=fm.action_rm, age_threshold=10)

    # Fresh → not old enough
    assert not act.is_old_enough(d)

    # Make the directory itself old → old enough
    _make_old(d, seconds_old=60)
    assert act.is_old_enough(d)


def test_1030_is_old_enough_recurses_into_nested_subdirs(tmp_path):
    """Newest mtime from deep within nested subdirs should control age."""
    top = tmp_path / "top"
    deep = top / "a" / "b" / "c"
    deep.mkdir(parents=True)
    deep_file = deep / "x.log"
    _touch(deep_file)

    act = fm.FileManager(fpattern="*", action=fm.action_rm, age_threshold=10)

    # Top dir and parents can be old...
    _make_old(top, seconds_old=60)
    _make_old(top / "a", seconds_old=60)
    _make_old(top / "a" / "b", seconds_old=60)

    # ...but a deep child is fresh → NOT old enough
    assert not act.is_old_enough(top)

    # Once the deep child is old, the whole dir becomes old enough
    _make_old(deep_file, seconds_old=60)
    assert act.is_old_enough(top)


def test_1045_dir_mtime_can_delay_even_when_files_old(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    f = d / "a.txt"
    _touch(f)
    act = fm.FileManager(fpattern="*", action=fm.action_rm, age_threshold=10)

    # Make the file old enough
    _make_old(f, seconds_old=60)
    # Bump directory mtime to "now" (simulate rename/add/remove)
    os.utime(d, None)

    # Dir should be considered young because its own mtime is recent
    assert not act.is_old_enough(d)

    # Make dir old as well
    _make_old(d, seconds_old=60)
    assert act.is_old_enough(d)


async def test_1100_act_no_action_when_not_old_enough(tmp_path, caplog, monkeypatch):
    f = tmp_path / "file.txt"
    _touch(f)
    # Age threshold 1 day; file is brand new
    act = fm.FileManager(fpattern="*", action=fm.action_rm, age_threshold=24 * 3600)

    await act.act(f)

    # File remains
    assert f.exists()
    # Log line shows "no action"
    assert any(
        "no action -- filepath not older" in rec.message for rec in caplog.records
    )


async def test_1200_action_exception_raised(tmp_path, caplog):
    f = tmp_path / "boom.txt"
    _touch(f)

    def bad_action(_):
        raise ValueError("boom")

    mgr = fm.FileManager(fpattern="*", action=bad_action, age_threshold=0)

    with pytest.raises(ValueError, match="boom"):
        await mgr.act(f)

    # File remains because action failed
    assert f.exists()
