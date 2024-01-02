"""Entrypoint for TMS."""


import asyncio
import logging

import htcondor  # type: ignore[import-untyped]

from .config import config_logging
from .starter import starter
from .stopper import stopper
from .watcher import watcher

LOGGER = logging.getLogger(__name__)


async def starter_loop() -> None:
    """Do the action."""

    for task in []:
        starter.start(
            task.taskforce_uuid,
            task.n_workers,
            task.spool,
            task.worker_memory_bytes,
            task.worker_disk_bytes,
            task.n_cores,
            task.max_worker_runtime,
            task.priority,
            task.client_args,
            task.client_startup_json_s3_url,
            task.image,
        )


async def watcher_loop() -> None:
    """explain."""

    for task in []:
        watcher.watch(
            task.cluster_id,
            task.n_workers,
        )


async def stopper_loop() -> None:
    """explain."""

    for task in []:
        stopper.stop(task.cluster_id)


def _create_loop(key: str) -> asyncio.Task[None]:
    funcs = {
        "starter": starter_loop,
        "watcher": watcher_loop,
        "stopper": stopper_loop,
    }
    return asyncio.create_task(funcs[key]())


async def main() -> None:
    """explain."""
    htcondor.set_subsystem("TOOL")
    htcondor.param["TOOL_DEBUG"] = "D_FULLDEBUG"
    # htcondor.param["TOOL_LOG"] = "log.txt"
    # htcondor.enable_log()
    htcondor.enable_debug()

    loops = {
        k: _create_loop(k)
        for k in [
            "starter",
            "watcher",
            "stopper",
        ]
    }

    while True:
        done, _ = await asyncio.wait(
            loops.values(),
            return_when=asyncio.FIRST_COMPLETED,
        )
        # restart any done tasks
        for key in loops:
            if loops[key] in done:
                loops[key] = _create_loop(key)


if __name__ == "__main__":
    config_logging()
    asyncio.run(main())
