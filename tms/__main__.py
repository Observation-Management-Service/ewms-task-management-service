"""Entrypoint for TMS."""


import asyncio
import logging
from typing import Any, AsyncIterator

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import RestClient

from . import utils
from .config import ENV, config_logging
from .starter import starter
from .stopper import stopper
from .watcher import watcher

LOGGER = logging.getLogger(__name__)


async def starter_loop() -> None:
    """Do the action."""

    # make connections -- do now so we don't have any surprises downstream
    schedd_obj = htcondor.Schedd()  # no auth need b/c we're on AP
    ewms_rc = RestClient(ENV.EWMS_ADDRESS, token=ENV.EWMS_AUTH)
    LOGGER.info("Connected to EWMS")

    async def next_one() -> dict[str, Any]:
        return await ewms_rc.request(  # type: ignore[no-any-return]
            "GET",
            "/taskforce/next",
            {"collector": ENV.COLLECTOR, "schedd": ENV.SCHEDD},
        )

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
        await utils.update_ewms_taskforce(
            ewms_rc,
            args["taskforce_uuid"],
            ewms_taskforce_attrs,
        )
        LOGGER.info("Sent taskforce info to EWMS")


async def watcher_loop() -> None:
    """explain."""

    # make connections -- do now so we don't have any surprises downstream
    schedd_obj = htcondor.Schedd()  # no auth need b/c we're on AP
    ewms_rc = RestClient(ENV.EWMS_ADDRESS, token=ENV.EWMS_AUTH)
    LOGGER.info("Connected to EWMS")

    async def iter_live_taskforces() -> AsyncIterator[dict[str, Any]]:
        while True:
            for one in await ewms_rc.request(
                "GET",
                "/taskforce/live",
                {"collector": ENV.COLLECTOR, "schedd": ENV.SCHEDD},
            ):
                yield one

    async for args in iter_live_taskforces():
        # TODO - figure managing multiple taskforces and remain stateless
        async for update in watcher.watch(
            schedd_obj,
            #
            args["taskforce_uuid"],
            args["cluster_id"],
            args["n_workers"],
        ):
            if not update:
                continue
            await utils.update_ewms_taskforce(
                ewms_rc,
                args["taskforce_uuid"],
                update,
            )


async def stopper_loop() -> None:
    """explain."""

    # make connections -- do now so we don't have any surprises downstream
    schedd_obj = htcondor.Schedd()  # no auth need b/c we're on AP
    ewms_rc = RestClient(ENV.EWMS_ADDRESS, token=ENV.EWMS_AUTH)
    LOGGER.info("Connected to EWMS")

    async def next_one() -> dict[str, Any]:
        return await ewms_rc.request(  # type: ignore[no-any-return]
            "GET",
            "/taskforce/abort",
            {"collector": ENV.COLLECTOR, "schedd": ENV.SCHEDD},
        )

    while args := await next_one():
        stopper.stop(
            schedd_obj,
            args["cluster_id"],
        )
        # TODO - confirm stop (otherwise ewms will request again -- good for stateless)
        # await utils.update_ewms_taskforce(ewms_rc, args["taskforce_uuid"])


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
