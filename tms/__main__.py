"""Entrypoint for TMS."""


import asyncio
import logging
from pathlib import Path

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import RestClient

from .config import ENV, config_logging
from .scalar import scalar_loop
from .watcher import watcher

LOGGER = logging.getLogger(__name__)


async def watcher_loop() -> None:
    """Watch over all job event log files and send EWMS taskforce updates."""
    in_progress: dict[Path, asyncio.Task[None]] = {}

    # make connections -- do now so we don't have any surprises downstream
    ewms_rc = RestClient(ENV.EWMS_ADDRESS, token=ENV.EWMS_AUTH)
    LOGGER.info("Connected to EWMS")

    while True:
        for jel_fpath in ENV.JOB_EVENT_LOG_DIR.iterdir():
            if jel_fpath in in_progress:
                continue
            task = asyncio.create_task(watcher.watch_job_event_log(jel_fpath, ewms_rc))
            await asyncio.sleep(0)  # start above task
            in_progress[jel_fpath] = task

        await asyncio.sleep(ENV.TMS_OUTER_LOOP_WAIT)


async def main() -> None:
    """explain."""
    htcondor.set_subsystem("TOOL")
    htcondor.param["TOOL_DEBUG"] = "D_FULLDEBUG"
    # htcondor.param["TOOL_LOG"] = "log.txt"
    # htcondor.enable_log()
    htcondor.enable_debug()

    loops = {
        asyncio.create_task(scalar_loop()): "scalar",
        asyncio.create_task(watcher_loop()): "watcher",
    }
    done, _ = await asyncio.wait(
        loops.keys(),
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in done:
        LOGGER.error(f"'{loops[task]}' asyncio task completed: {task}")


if __name__ == "__main__":
    config_logging()
    asyncio.run(main())
