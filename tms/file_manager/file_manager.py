"""Monitor and process files according to specified actions every 60 seconds."""

import asyncio
import glob
import logging
import os
import shutil
import tarfile
import time
from dataclasses import dataclass
from typing import Literal

LOGGER = logging.getLogger(__name__)


@dataclass
class FilepathAction:
    """What action to take on the filepath."""

    action: Literal["rm", "mv", "tar"]
    min_age_secs: int  # Only act if file is older than this

    dest: str | None = None  # not all actions need destinations


ACTION_MAP: dict[str, FilepathAction] = {
    "/tmp/data/*.log": FilepathAction("rm", 600),
    "/tmp/data/to-move/*": FilepathAction("mv", 600, dest="/tmp/moved"),
    "/tmp/data/to-archive/*": FilepathAction("tar", 1800, "/tmp/archives/data.tar.gz"),
}


def is_old_enough(filepath: str, age_threshold: int) -> bool:
    """Is the filepath older than the age_threshold"""
    return (time.time() - os.path.getmtime(filepath)) >= age_threshold


def process_action(fpath: str, fa: FilepathAction) -> None:
    try:
        if not is_old_enough(fpath, fa.min_age_secs):
            return

        match fa.action:
            case "rm":
                os.remove(fpath)
                LOGGER.info(f"done: rm {fpath}")

            case "mv":
                assert fa.dest is not None
                os.makedirs(fa.dest, exist_ok=True)
                shutil.move(fpath, fa.dest)
                LOGGER.info(f"done: mv {fpath} → {fa.dest}")

            case "tar":
                assert fa.dest is not None
                mode = "w:gz" if fa.dest.endswith(".gz") else "w"
                with tarfile.open(fa.dest, mode) as tar:
                    tar.add(fpath, arcname=os.path.basename(fpath))
                os.remove(fpath)
                LOGGER.info(f"done: tar {fpath} → {fa.dest} + rm {fpath}")

            case _:
                LOGGER.warning(f"Unknown action: {fa.action}")

    except Exception as e:
        LOGGER.error(f"Error processing {fpath} with action={fa}: {e}")


async def run() -> None:
    """Run the file manager loop."""

    while True:
        await asyncio.sleep(60)

        for fpath_pattern, file_action in ACTION_MAP.items():
            for fpath in glob.glob(fpath_pattern):
                process_action(fpath, file_action)
