"""Entrypoint for TMS."""


import asyncio
import logging

import htcondor  # type: ignore[import-untyped]

from .config import config_logging
from .starter import starter
from .stopper import stopper
from .watcher import watcher

LOGGER = logging.getLogger(__name__)


def starter_loop() -> None:
    """Do the action."""

    for task in []:
        starter.start(
            task.scan_id,
            task.cluster_uuid,
            task.n_workers,
            task.spool,
            task.worker_memory_bytes,
            task.worker_disk_bytes,
            task.n_cores,
            task.max_worker_runtime,
            task.priority,
            task.client_args,
            task.client_startup_json_s3,
            task.image,
        )


def watcher_loop() -> None:
    """explain."""

    for task in []:
        watcher.watch(
            task.cluster_id,
            task.n_workers,
        )


def stopper_loop() -> None:
    """explain."""

    for task in []:
        stopper.stop(task.cluster_id)


async def main() -> None:
    """explain."""
    htcondor.set_subsystem("TOOL")
    htcondor.param["TOOL_DEBUG"] = "D_FULLDEBUG"
    # htcondor.param["TOOL_LOG"] = "log.txt"
    # htcondor.enable_log()
    htcondor.enable_debug()


if __name__ == "__main__":
    config_logging()
    asyncio.run(main())
