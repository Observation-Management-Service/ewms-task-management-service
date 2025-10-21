"""Loops over JEL files, starting watcher instances."""

import asyncio
import logging
from pathlib import Path

from rest_tools.client import RestClient

from . import watcher
from ..config import ENV
from ..utils import JELFileLogic

LOGGER = logging.getLogger(__name__)


async def run(ewms_rc: RestClient) -> None:
    """Watch over all JEL files and send EWMS taskforce updates."""
    LOGGER.info("Activated.")

    # track which JEL paths are already being watched
    in_progress: set[Path] = set()

    # https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup
    # on task fail, cancel others then raise original exception(s)
    async with asyncio.TaskGroup() as tg:
        while True:
            LOGGER.debug(  # very chatty
                f"Analyzing JEL directory for new logs ({ENV.JOB_EVENT_LOG_DIR})..."
            )
            for jel_fpath in ENV.JOB_EVENT_LOG_DIR.iterdir():
                if not JELFileLogic.is_valid(jel_fpath):
                    continue

                # skip if already in progress
                if jel_fpath in in_progress:
                    continue

                # mark as in-progress
                in_progress.add(jel_fpath)

                # go!
                LOGGER.info(f"Creating new watcher for JEL {jel_fpath}...")
                jel_watcher = watcher.JobEventLogWatcher(jel_fpath, ewms_rc)
                task = tg.create_task(jel_watcher.start())

                # when the watcher exits (normal/error), allow re-watching this path
                task.add_done_callback(lambda _t, p=jel_fpath: in_progress.remove(p))  # type: ignore

            # wait before scanning for new logs again
            await asyncio.sleep(ENV.TMS_OUTER_LOOP_WAIT)
