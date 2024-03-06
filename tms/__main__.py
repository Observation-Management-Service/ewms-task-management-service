"""Entrypoint for TMS."""


import asyncio
import logging
from pathlib import Path

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import ClientCredentialsAuth

from .config import ENV, config_logging
from .scalar.scalar import scalar_loop
from .utils import AppendOnlyList, TaskforceMonitor
from .watcher import watcher

LOGGER = logging.getLogger(__name__)


async def watcher_loop(tmonitors: AppendOnlyList[TaskforceMonitor]) -> None:
    """Watch over all JEL files and send EWMS taskforce updates."""
    LOGGER.info("Starting watcher...")

    in_progress: list[Path] = []

    # make connections -- do now so we don't have any surprises downstream
    LOGGER.info("Connecting to EWMS...")
    ewms_rc = ClientCredentialsAuth(
        ENV.EWMS_ADDRESS,
        ENV.EWMS_TOKEN_URL,
        ENV.EWMS_CLIENT_ID,
        ENV.EWMS_CLIENT_SECRET,
    )

    # https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup
    # on task fail, cancel others then raise original exception(s)
    async with asyncio.TaskGroup() as tg:
        while True:
            LOGGER.info(
                f"Analyzing JEL directory for new logs ({ENV.JOB_EVENT_LOG_DIR})..."
            )
            for jel_fpath in ENV.JOB_EVENT_LOG_DIR.iterdir():
                # check/append
                if jel_fpath in in_progress:
                    continue
                else:
                    in_progress.append(jel_fpath)
                # go!
                LOGGER.info(f"Creating new JEL watcher for {jel_fpath}...")
                tg.create_task(
                    watcher.watch_job_event_log(
                        jel_fpath,
                        ewms_rc,
                        tmonitors,
                    )
                )

            await asyncio.sleep(ENV.TMS_OUTER_LOOP_WAIT)  # start all above tasks


async def main() -> None:
    """explain."""
    LOGGER.info("Starting up...")

    htcondor.set_subsystem("TOOL")
    htcondor.param["TOOL_DEBUG"] = "D_FULLDEBUG"
    # htcondor.param["TOOL_LOG"] = "log.txt"
    # htcondor.enable_log()
    htcondor.enable_debug()

    tmonitors: AppendOnlyList[TaskforceMonitor] = AppendOnlyList()

    LOGGER.info("Starting tasks...")

    # https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup
    # on task fail, cancel others then raise original exception(s)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(scalar_loop(tmonitors))
        tg.create_task(watcher_loop(tmonitors))

    LOGGER.info("Done")


if __name__ == "__main__":
    config_logging()
    asyncio.run(main())
