"""Entrypoint for TMS."""


import asyncio
import logging
from pathlib import Path
from typing import Any

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import RestClient

from . import utils
from .config import ENV, OUTER_LOOP_WAIT, config_logging
from .starter import starter
from .stopper import stopper
from .watcher import watcher

LOGGER = logging.getLogger(__name__)


async def starter_loop() -> None:
    """Listen to EWMS and start designated taskforces."""

    # make connections -- do now so we don't have any surprises downstream
    schedd_obj = htcondor.Schedd()  # no auth need b/c we're on AP
    ewms_rc = RestClient(ENV.EWMS_ADDRESS, token=ENV.EWMS_AUTH)
    LOGGER.info("Connected to EWMS")

    async def next_one() -> dict[str, Any]:
        """Get the next taskforce requested for this collector + schedd."""
        return await ewms_rc.request(  # type: ignore[no-any-return]
            "GET",
            "/taskforce/start",
            {"collector": ENV.COLLECTOR, "schedd": ENV.SCHEDD},
        )

    while True:
        while args := await next_one():
            ewms_taskforce_attrs = await starter.start(
                schedd_obj,
                utils.ewms_aborted_taskforce(ewms_rc, args["taskforce_uuid"]),
                #
                args["taskforce_uuid"],
                args["n_workers"],
                args["spool"],
                args["worker_memory_bytes"],
                args["worker_disk_bytes"],
                args["n_cores"],
                args["max_worker_runtime"],
                args["priority"],
                args["client_args"],
                args["client_startup_json_s3_url"],
                args["image"],
            )
            # confirm start (otherwise ewms will request this one again -- good for statelessness)
            await ewms_rc.request(
                "PATCH",
                f"/taskforce/start/{args['taskforce_uuid']}",
                ewms_taskforce_attrs,
            )
            LOGGER.info("Sent taskforce info to EWMS")

        await asyncio.sleep(OUTER_LOOP_WAIT)


async def watcher_loop() -> None:
    """Watch over all job event log files and send EWMS taskforce updates."""
    in_progress: dict[Path, asyncio.Task[None]] = {}

    while True:
        for jel_fpath in ENV.JOB_EVENT_LOG_DIR.iterdir():
            if jel_fpath in in_progress:
                continue
            task = asyncio.create_task(watcher.watch_job_event_log(jel_fpath))
            in_progress[jel_fpath] = task

        await asyncio.sleep(OUTER_LOOP_WAIT)


async def stopper_loop() -> None:
    """Listen to EWMS and stop designated taskforces."""

    # make connections -- do now so we don't have any surprises downstream
    schedd_obj = htcondor.Schedd()  # no auth need b/c we're on AP
    ewms_rc = RestClient(ENV.EWMS_ADDRESS, token=ENV.EWMS_AUTH)
    LOGGER.info("Connected to EWMS")

    async def next_one() -> dict[str, Any]:
        """Get the next taskforce requested for this collector + schedd."""
        return await ewms_rc.request(  # type: ignore[no-any-return]
            "GET",
            "/taskforce/stop",
            {"collector": ENV.COLLECTOR, "schedd": ENV.SCHEDD},
        )

    while True:
        while args := await next_one():
            stopper.stop(
                schedd_obj,
                args["cluster_id"],
            )
            # confirm stop (otherwise ewms will request this one again -- good for statelessness)
            await ewms_rc.request(
                "DELETE",
                f"/taskforce/stop/{args['taskforce_uuid']}",
            )

        await asyncio.sleep(OUTER_LOOP_WAIT)


def _create_loop_task(key: str) -> asyncio.Task[None]:
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
        k: _create_loop_task(k)
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
                loops[key] = _create_loop_task(key)


if __name__ == "__main__":
    config_logging()
    asyncio.run(main())
