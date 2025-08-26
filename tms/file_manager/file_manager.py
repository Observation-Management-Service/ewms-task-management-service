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
from ..utils import is_jel_no_longer_used

LOGGER = logging.getLogger(__name__)


@dataclass
class FilepathAction:
    """What action to take on the filepath."""

    action: Literal["rm", "mv", "tar_gz"]
    age_threshold: int  # Only act if file is older than this

    dest: Path | None = None  # not all actions need destinations

    precheck: Callable[[Path], Awaitable[bool]] | None = None

    def __post_init__(self):
        if self.dest and self.dest.exists():
            raise RuntimeError(f"destination already exists: {self.dest}")

    def _rm(self, fpath: Path) -> None:
        """rm the file."""
        os.remove(fpath)
        LOGGER.info(f"done: rm {fpath}")

    def _mv(self, fpath: Path) -> None:
        """mv the file."""
        if not self.dest:
            raise RuntimeError(f"destination not given for '{self.action}' on {fpath=}")

        os.makedirs(self.dest, exist_ok=True)
        shutil.move(fpath, self.dest)

        LOGGER.info(f"done: mv {fpath} → {self.dest}")

    def _tar_gz(self, src: Path) -> None:
        """Tar+gzip the directory and remove the source afterwards."""
        if not self.dest:
            raise RuntimeError(f"destination not given for '{self.action}' on {src=}")
        if not self.dest.is_dir():
            raise NotADirectoryError(f"{self.dest=}")
        if not src.is_dir():
            raise NotADirectoryError(f"{src=}")

        self.dest.mkdir(parents=True, exist_ok=True)
        tar_dest = self.dest / f"{src.name}.tar.gz"

        with tarfile.open(tar_dest, "w:gz") as tar:
            tar.add(src, arcname=src.name)  # preserve top-level directory

        shutil.rmtree(src)  # remove the directory safely

        LOGGER.info(f"done: tar.gz {src} → {tar_dest} + rm {src}")

    def is_old_enough(self, fpath: Path) -> bool:
        """Is the filepath older than the age_threshold"""
        return (time.time() - os.path.getmtime(fpath)) >= self.age_threshold

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


ACTION_MAP: dict[str, FilepathAction] = {
    str(ENV.JOB_EVENT_LOG_DIR / "tms-*.log"): FilepathAction(  # ex: # tms-2025-8-26.log
        "rm",
        age_threshold=ENV.JOB_EVENT_LOG_MODIFICATION_EXPIRY,
        precheck=is_jel_no_longer_used,
    ),
    str(ENV.JOB_EVENT_LOG_DIR / "ewms-taskforce-*"): FilepathAction(
        "tar_gz",
        age_threshold=600,
        dest=Path("/tmp/moved"),
    ),
    "/tmp/data/to-archive/*": FilepathAction(
        "tar",
        age_threshold=1800,
        dest=Path("/tmp/archives/data.tar.gz"),
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
