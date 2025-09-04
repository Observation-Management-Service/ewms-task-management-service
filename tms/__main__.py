"""Entrypoint for TMS."""

import asyncio
import logging
from pathlib import Path

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import ClientCredentialsAuth, RestClient

from .config import ENV, config_logging
from .file_manager import file_manager
from .scalar.scalar import scalar_loop
from .utils import AppendOnlyList, JELFileLogic, TaskforceMonitor
from .watcher import watcher

LOGGER = logging.getLogger(__name__)


async def watcher_loop(
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


async def main() -> None:
    """explain."""
    LOGGER.info("TMS Activated.")

    htcondor.set_subsystem("TOOL")
    htcondor.param["TOOL_DEBUG"] = "D_FULLDEBUG"
    # htcondor.param["TOOL_LOG"] = "log.txt"
    # htcondor.enable_log()
    htcondor.enable_debug()

    tmonitors: AppendOnlyList[TaskforceMonitor] = AppendOnlyList()

    LOGGER.info("Connecting to EWMS...")
    ewms_rc = ClientCredentialsAuth(
        ENV.EWMS_ADDRESS,
        ENV.EWMS_TOKEN_URL,
        ENV.EWMS_CLIENT_ID,
        ENV.EWMS_CLIENT_SECRET,
    )

    LOGGER.info("Starting tasks...")

    # https://docs.python.org/3/library/asyncio-task.html#asyncio.TaskGroup
    # on task fail, cancel others then raise original exception(s)
    async with asyncio.TaskGroup() as tg:
        # scalar
        LOGGER.info("Firing off scalar loop...")
        tg.create_task(scalar_loop(tmonitors, ewms_rc))

        # watcher
        LOGGER.info("Firing off watcher loop...")
        tg.create_task(watcher_loop(tmonitors, ewms_rc))

        # file manager
        LOGGER.info("Firing off file manager...")
        tg.create_task(file_manager.run(ewms_rc))

    LOGGER.info("Done")


if __name__ == "__main__":
    config_logging()
    asyncio.run(main())
