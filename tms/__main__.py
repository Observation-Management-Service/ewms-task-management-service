"""Entrypoint for TMS."""


import asyncio
import logging
import time
from typing import Any

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


class EveryXSeconds:
    """Keep track of durations."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self._last_time = time.time()

    def has_been_x_seconds(self) -> bool:
        """Has it been at least `self.seconds` since last time?"""
        yes = time.time() - self._last_time >= self.seconds
        if yes:
            self._last_time = time.time()
        return yes


async def watcher_loop() -> None:
    """explain."""

    # make connections -- do now so we don't have any surprises downstream
    schedd_obj = htcondor.Schedd()  # no auth need b/c we're on AP
    ewms_rc = RestClient(ENV.EWMS_ADDRESS, token=ENV.EWMS_AUTH)
    LOGGER.info("Connected to EWMS")

    statuses: dict[str, Any] = {}
    time_tracker = EveryXSeconds(60)

    jel_fpath = "bar"
    jel = htcondor.JobEventLog(jel_fpath)
    jel_index = -1

    while True:
        # wait for job log to populate (more)
        while not time_tracker.has_been_x_seconds():
            await asyncio.sleep(1)

        # get events -- exit when no more events, or took too long
        for event in jel.events(stop_after=0):  # 0 -> only get currently available
            jel_index += 1
            taskforce_uuid = "foo"
            taskforce_update = watcher.translate(
                statuses.get(taskforce_uuid, None),
                event,
            )
            statuses.update({taskforce_uuid: taskforce_update})
            if time_tracker.has_been_x_seconds():
                break
            await asyncio.sleep(0)  # since htcondor is not async

        # send -- TODO do one big update? that way it won't intermittently fail
        for taskforce_uuid in statuses:
            taskforce_update = statuses.pop(taskforce_uuid)
            if not taskforce_update:
                continue
            taskforce_update.update({"jel_index": jel_index})
            await utils.update_ewms_taskforce(
                ewms_rc,
                taskforce_uuid,
                taskforce_update,
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
