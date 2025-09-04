"""Entrypoint for TMS."""

import asyncio
import logging

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import ClientCredentialsAuth

from .config import ENV, config_logging
from .file_manager import file_manager
from .scalar import scalar
from .utils import AppendOnlyList, TaskforceMonitor
from .watcher import watcher_loop

LOGGER = logging.getLogger(__name__)


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
        tg.create_task(scalar.run(tmonitors, ewms_rc))

        # watcher
        LOGGER.info("Firing off watcher loop...")
        tg.create_task(watcher_loop.run(tmonitors, ewms_rc))

        # file manager
        LOGGER.info("Firing off file manager...")
        tg.create_task(file_manager.run(ewms_rc))


if __name__ == "__main__":
    config_logging()
    asyncio.run(main())
    LOGGER.info("Done.")
