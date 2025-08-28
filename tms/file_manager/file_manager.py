"""Monitor and process files according to specified actions every 60 seconds."""

import asyncio
import glob
import logging
import os
import shutil
import tarfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Literal

from ..config import ENV
from ..utils import JELFileLogic, TaskforceDirLogic

LOGGER = logging.getLogger(__name__)


@dataclass
class FpathAction:
    """What action to take on the filepath."""

    action: Literal["rm", "mv", "tar_gz"]
    age_threshold: int  # Only act if file is older than this

    dest: Path | None = None  # not all actions need destinations

    precheck: Callable[[Path], Awaitable[bool]] | None = None

    def _rm(self, fpath: Path) -> None:
        """rm the file."""
        os.remove(fpath)
        LOGGER.info(f"done: rm {fpath}")

    def _mv(self, fpath: Path) -> None:
        """mv the file."""
        if not self.dest:
            raise RuntimeError(f"destination not given for '{self.action}' on {fpath=}")
        if self.dest.exists():
            raise RuntimeError(f"destination already exists: {self.dest}")

        os.makedirs(self.dest, exist_ok=True)
        shutil.move(fpath, self.dest)

        LOGGER.info(f"done: mv {fpath} → {self.dest}")

    def _tar_gz(self, src: Path) -> None:
        """Tar+gzip the directory and remove the source afterwards."""
        if not self.dest:
            raise RuntimeError(f"destination not given for '{self.action}' on {src=}")
        if not src.is_dir():
            raise NotADirectoryError(f"{src=}")

        self.dest.mkdir(parents=True, exist_ok=True)
        tar_dest = self.dest / f"{src.name}.tar.gz"

        with tarfile.open(tar_dest, "w:gz") as tar:
            tar.add(src, arcname=src.name)  # preserve top-level directory

        shutil.rmtree(src)  # remove the directory safely

        LOGGER.info(f"done: tar.gz {src} → {tar_dest} + rm {src}")

    def is_old_enough(self, fpath: Path) -> bool:
        """Is the file/dir older than the age_threshold?"""
        threshold_time = time.time() - self.age_threshold

        if fpath.is_dir():

            # Walk through files; if any are newer than threshold -> not old enough
            for p in fpath.rglob("*"):
                # short circuit logic (don't traverse more than needed)
                if p.is_file() and p.stat().st_mtime > threshold_time:
                    return False
            # Notes:
            #   - If the dir had no files *OR* had only old files files, check dir's mtime.
            #   - A dir's mtime updates when its entries change (create/rm/mv files or subdirs),
            #       *NOT* when the contents of its descendants change.
            return fpath.stat().st_mtime <= threshold_time

        # Plain file (or symlink to a file)
        else:
            return fpath.stat().st_mtime <= threshold_time

    async def act(self, fpath: Path) -> None:
        """Perform action on filepath, if the file is old enough."""
        if not fpath.exists():
            raise FileNotFoundError(fpath)

        if self.precheck and not await self.precheck(fpath):
            LOGGER.warning(
                f"precheck failed for {fpath=} -- will try again later in {ENV.TMS_FILE_MANAGER_INTERVAL}"
            )
            return

        if not self.is_old_enough(fpath):
            LOGGER.info(
                f"no action -- filepath not older than {self.age_threshold} seconds {fpath=}"
            )
            return

        LOGGER.info(f"performing action '{self.action}'...")
        actions = {
            "rm": self._rm,
            "mv": self._mv,
            "tar_gz": self._tar_gz,
        }

        # get & call function
        try:
            return actions[self.action](fpath)
        except KeyError:
            raise ValueError(f"Unknown action: {self.action}")


ACTION_MAP: dict[str, FpathAction] = {
    #
    # ex: 2025-8-26.tms.jel
    str(JELFileLogic.parent / f"*{JELFileLogic.suffix}"): FpathAction(
        "rm",
        age_threshold=ENV.JOB_EVENT_LOG_MODIFICATION_EXPIRY,
        precheck=JELFileLogic.is_no_longer_used,
    ),
    #
    # ex: ewms-taskforce-TF-685e6219-e85461b3-f8dc0d3c-6e4a5d72
    str(TaskforceDirLogic.parent / f"{TaskforceDirLogic.prefix}*"): FpathAction(
        "tar_gz",
        age_threshold=ENV.TASKFORCE_DIRS_EXPIRY,
        dest=ENV.JOB_EVENT_LOG_DIR,
    ),
    #
    # ex: ewms-taskforce-TF-685e6219-e85461b3-f8dc0d3c-6e4a5d72.tar.gz
    str(TaskforceDirLogic.parent / f"{TaskforceDirLogic.prefix}*.tar.gz"): FpathAction(
        "rm",
        age_threshold=ENV.TASKFORCE_DIRS_TAR_EXPIRY,
    ),
}


async def run() -> None:
    """Run the file manager loop."""
    await asyncio.sleep(60)

    while True:

        LOGGER.info("inspecting filepaths...")

        for fpath_pattern, file_action in ACTION_MAP.items():
            LOGGER.info(f"searching filepath pattern: {fpath_pattern}")
            for fpath in glob.glob(fpath_pattern):
                LOGGER.info(f"looking at {fpath=}")
                await file_action.act(Path(fpath))
                await asyncio.sleep(0)  # let the TMS do other scheduled things

        await asyncio.sleep(ENV.TMS_FILE_MANAGER_INTERVAL)  # O(hours)
