"""Entrypoint for TMS."""


import asyncio
import logging
from pathlib import Path

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import RestClient

from .config import ENV, config_logging
from .scalar.scalar import scalar_loop
from .utils import AppendOnlyList, TaskforceMonitor
from .watcher import watcher

LOGGER = logging.getLogger(__name__)


async def watcher_loop(tmonitors: AppendOnlyList[TaskforceMonitor]) -> None:
    """Watch over all job event log files and send EWMS taskforce updates."""
    in_progress: dict[Path, asyncio.Task[None]] = {}

    # make connections -- do now so we don't have any surprises downstream
    ewms_rc = RestClient(ENV.EWMS_ADDRESS, token=ENV.EWMS_AUTH)
    LOGGER.info("Connected to EWMS")

    while True:
        for jel_fpath in ENV.JOB_EVENT_LOG_DIR.iterdir():
            if jel_fpath in in_progress:
                continue
            task = asyncio.create_task(
                watcher.watch_job_event_log(
                    jel_fpath,
                    ewms_rc,
                    tmonitors,
                )
            )
            in_progress[jel_fpath] = task

        await asyncio.sleep(ENV.TMS_OUTER_LOOP_WAIT)  # start all above tasks


async def main() -> None:
    """explain."""
    htcondor.set_subsystem("TOOL")
    htcondor.param["TOOL_DEBUG"] = "D_FULLDEBUG"
    # htcondor.param["TOOL_LOG"] = "log.txt"
    # htcondor.enable_log()
    htcondor.enable_debug()

    tmonitors: AppendOnlyList[TaskforceMonitor] = AppendOnlyList()

    # https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup
    # on task fail, cancel others then raise original exception(s)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(scalar_loop(tmonitors))
        tg.create_task(watcher_loop(tmonitors))

    LOGGER.info("Done")


if __name__ == "__main__":
    config_logging()
    asyncio.run(main())
