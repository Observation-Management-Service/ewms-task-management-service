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
from typing import Literal

LOGGER = logging.getLogger(__name__)


@dataclass
class FilepathAction:
    """What action to take on the filepath."""

    action: Literal["rm", "mv", "tar"]
    age_threshold: int  # Only act if file is older than this

    dest: Path | None = None  # not all actions need destinations

    def __post_init__(self):
        if self.dest and self.dest.exists():
            raise RuntimeError(f"destination already exists: {self.dest}")

    def _rm(self, fpath: Path) -> None:
        os.remove(fpath)
        LOGGER.info(f"done: rm {fpath}")

    def _mv(self, fpath: Path) -> None:
        assert self.dest is not None
        os.makedirs(self.dest, exist_ok=True)
        shutil.move(fpath, self.dest)
        LOGGER.info(f"done: mv {fpath} → {self.dest}")

    def _tar(self, fpath: Path) -> None:
        assert self.dest is not None
        mode = "w:gz" if self.dest.suffix == ".gz" else "w"
        with tarfile.open(self.dest, mode) as tar:
            tar.add(fpath, arcname=os.path.basename(fpath))
        os.remove(fpath)
        LOGGER.info(f"done: tar {fpath} → {self.dest} + rm {fpath}")

    def is_old_enough(self, fpath: Path) -> bool:
        """Is the filepath older than the age_threshold"""
        return (time.time() - os.path.getmtime(fpath)) >= self.age_threshold

    def act(self, fpath: Path) -> None:
        """Perform action on filepath, if the file is old enough."""
        if not fpath.exists():
            raise FileNotFoundError(fpath)

        if not self.is_old_enough(fpath):
            return

        actions = {
            "rm": self._rm,
            "mv": self._mv,
            "tar": self._tar,
        }

        try:
            actions[self.action](fpath)
        except KeyError:
            raise ValueError(f"Unknown action: {self.action}")


ACTION_MAP: dict[str, FilepathAction] = {
    "/tmp/data/*.log": FilepathAction(
        "rm",
        age_threshold=600,
    ),
    "/tmp/data/to-move/*": FilepathAction(
        "mv",
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

    while True:
        await asyncio.sleep(60)

        for fpath_pattern, file_action in ACTION_MAP.items():
            for fpath in glob.glob(fpath_pattern):
                file_action.act(Path(fpath))
