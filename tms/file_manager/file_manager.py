"""Monitor and process files according to specified actions every 60 seconds."""

import asyncio
import glob
import logging
import os
import shutil
import tarfile
import time
from functools import partial
from pathlib import Path
from typing import Awaitable, Callable

from ..config import ENV
from ..utils import JELFileLogic, TaskforceDirLogic

LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Action helpers (can be passed directly or via functools.partial/lambda)
# -----------------------------------------------------------------------------


def action_rm(fpath: Path) -> None:
    """rm the file/dir."""
    if not fpath.exists():
        LOGGER.info(f"skip: already absent {fpath}")
        return

    if fpath.is_dir():
        shutil.rmtree(fpath)
    else:
        os.remove(fpath)

    LOGGER.info(f"done: rm {fpath}")


def action_mv(fpath: Path, *, dest: Path) -> None:
    """mv the file/dir (bash semantics)."""
    if not dest:
        raise RuntimeError(f"destination not given for 'mv' on {fpath=}")

    if dest.exists():
        if dest.is_dir():
            final = dest / fpath.name
        else:
            final = dest  # overwrite permitted (bash-like)
    else:
        # missing dest → treat as rename; do NOT create parent dirs
        final = dest

    shutil.move(str(fpath), str(final))
    LOGGER.info(f"done: mv {fpath} → {final}")


def action_tar_gz(fpath: Path, *, dest: Path) -> None:
    """Tar+gzip the directory and remove the source afterwards."""
    if not dest:
        raise RuntimeError(f"destination not given for 'tar_gz' on {fpath=}")
    if not fpath.is_dir():
        raise NotADirectoryError(f"{fpath=}")

    tar_dest = dest / f"{fpath.name}.tar.gz"

    if tar_dest.exists():
        raise FileExistsError(f"archive already exists: {tar_dest}")

    dest.mkdir(parents=True, exist_ok=True)

    with tarfile.open(tar_dest, "w:gz") as tar:
        tar.add(fpath, arcname=fpath.name)  # preserve top-level directory

    shutil.rmtree(fpath)
    LOGGER.info(f"done: tar.gz {fpath} → {tar_dest} + rm {fpath}")


# -----------------------------------------------------------------------------
# FileManager
# -----------------------------------------------------------------------------


class FileManager:
    """What action to take on the filepath."""

    def __init__(
        self,
        fpattern: str,
        action: Callable[[Path], None],
        age_threshold: int,
        precheck: Callable[[Path], Awaitable[bool]] | None = None,
    ):
        self.fpattern = fpattern
        self.action = action
        self.age_threshold = age_threshold  # Only act if file is older than this
        self.precheck = precheck

    def is_old_enough(self, fpath: Path) -> bool:
        """Is the file/dir older than the age_threshold?"""
        threshold_time = time.time() - self.age_threshold

        if fpath.is_dir():

            # Walk through files; if any are newer than threshold -> not old enough
            for p in fpath.rglob("*"):
                # short circuit logic (don't traverse more than needed)
                try:
                    if p.is_file() and p.stat().st_mtime > threshold_time:
                        return False
                except FileNotFoundError:
                    continue

            # Notes:
            #   - If the dir had no files *OR* had only old files, check dir's mtime.
            #   - A dir's mtime updates when its entries change (create/rm/mv files or subdirs),
            #       *NOT* when the contents of its descendants change.
            try:
                return fpath.stat().st_mtime <= threshold_time
            except FileNotFoundError:
                return False

        # Plain file (or symlink to a file)
        else:
            try:
                return fpath.stat().st_mtime <= threshold_time
            except FileNotFoundError:
                return False

    async def act(self, fpath: Path) -> bool:
        """Perform action on filepath, if the file is old enough."""
        if not fpath.exists():
            raise FileNotFoundError(fpath)

        if self.precheck is not None:
            if not await self.precheck(fpath):
                LOGGER.warning(
                    f"precheck failed for {fpath=} -- will try again later in {ENV.TMS_FILE_MANAGER_INTERVAL}"
                )
                return False

        if not self.is_old_enough(fpath):
            LOGGER.debug(
                f"no action -- filepath not older than {self.age_threshold} seconds {fpath=}"
            )
            return False

        LOGGER.info(f"performing action {self.action} on {fpath}")
        self.action(fpath)
        return True


# -----------------------------------------------------------------------------
# MAIN_LIST
# -----------------------------------------------------------------------------


MAIN_LIST: list[FileManager] = [
    #
    # ex: 2025-8-26.tms.jel
    FileManager(
        str(JELFileLogic.parent / f"*{JELFileLogic.suffix}"),
        action=action_rm,
        age_threshold=ENV.JOB_EVENT_LOG_MODIFICATION_EXPIRY,
        precheck=JELFileLogic.is_no_longer_used,
    ),
    #
    # ex: ewms-taskforce-TF-685e6219-e85461b3-f8dc0d3c-6e4a5d72
    FileManager(
        str(TaskforceDirLogic.parent / f"{TaskforceDirLogic.prefix}*"),
        action=partial(action_tar_gz, dest=ENV.JOB_EVENT_LOG_DIR),
        age_threshold=ENV.TASKFORCE_DIRS_EXPIRY,
    ),
    #
    # ex: ewms-taskforce-TF-685e6219-e85461b3-f8dc0d3c-6e4a5d72.tar.gz
    FileManager(
        str(TaskforceDirLogic.parent / f"{TaskforceDirLogic.prefix}*.tar.gz"),
        action=action_rm,
        age_threshold=ENV.TASKFORCE_DIRS_TAR_EXPIRY,
    ),
]


# -----------------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------------


async def run() -> None:
    """Run the file manager loop."""
    await asyncio.sleep(60)

    while True:

        LOGGER.info("inspecting filepaths...")
        n_actions = 0

        for fm in MAIN_LIST:
            LOGGER.debug(f"searching filepath pattern: {fm.fpattern}")

            for fpath in [Path(p) for p in glob.glob(fm.fpattern)]:
                LOGGER.debug(f"looking at {fpath=}")
                try:
                    n_actions += int(await fm.act(fpath))  # bool -> 1/0
                except Exception:
                    LOGGER.exception(f"action failed for {fpath=}")
                    continue
                else:
                    await asyncio.sleep(0)  # let the TMS do other scheduled things

        LOGGER.info(
            f"done with inspecting filepaths -- {n_actions} actions "
            f"(next round in {ENV.TMS_FILE_MANAGER_INTERVAL}s)"
        )

        await asyncio.sleep(ENV.TMS_FILE_MANAGER_INTERVAL)  # O(hours)
