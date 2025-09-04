"""Loops over JEL files, starting watcher instances."""

import asyncio
import logging
from pathlib import Path

import htcondor  # type: ignore[import-untyped]
from htcondor import classad  # type: ignore[import-untyped]
from rest_tools.client import RestClient

from . import watcher
from ..config import ENV
from ..utils import AppendOnlyList, JELFileLogic, TaskforceMonitor

LOGGER = logging.getLogger(__name__)


async def run(
    tmonitors: AppendOnlyList[TaskforceMonitor],
    ewms_rc: RestClient,
) -> None:
    """Watch over all JEL files and send EWMS taskforce updates."""
    LOGGER.info("Activated.")

    in_progress: list[Path] = []

    # https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup
    # on task fail, cancel others then raise original exception(s)
    async with asyncio.TaskGroup() as tg:
        while True:
            LOGGER.info(
                f"Analyzing JEL directory for new logs ({ENV.JOB_EVENT_LOG_DIR})..."
            )
            for jel_fpath in ENV.JOB_EVENT_LOG_DIR.iterdir():
                if not JELFileLogic.is_valid(jel_fpath):
                    continue

                # check/append
                if jel_fpath in in_progress:
                    continue
                else:
                    in_progress.append(jel_fpath)

                # go!
                LOGGER.info(f"Creating new JEL watcher for {jel_fpath}...")
                jel_watcher = watcher.JobEventLogWatcher(
                    jel_fpath,
                    ewms_rc,
                    tmonitors,
                )
                tg.create_task(jel_watcher.start())

            await asyncio.sleep(ENV.TMS_OUTER_LOOP_WAIT)  # start all above tasks
