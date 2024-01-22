"""Scalar entrypoint."""


import asyncio
import logging
from typing import Any

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import RestClient

from .. import utils
from ..config import ENV
from . import starter, stopper

LOGGER = logging.getLogger(__name__)


async def next_to_start(ewms_rc: RestClient) -> dict[str, Any]:
    """Get the next taskforce requested for this collector + schedd."""
    return await ewms_rc.request(  # type: ignore[no-any-return]
        "GET",
        "/tms/taskforce/pending",
        {"collector": ENV.COLLECTOR, "schedd": ENV.SCHEDD},
    )


async def next_to_stop(ewms_rc: RestClient) -> dict[str, Any]:
    """Get the next taskforce requested for this collector + schedd."""
    return await ewms_rc.request(  # type: ignore[no-any-return]
        "GET",
        "/tms/taskforce/stop",
        {"collector": ENV.COLLECTOR, "schedd": ENV.SCHEDD},
    )


async def scalar_loop() -> None:
    """Listen to EWMS and start and/or designated taskforces."""

    # make connections -- do now so we don't have any surprises downstream
    schedd_obj = htcondor.Schedd()  # no auth need b/c we're on AP
    ewms_rc = RestClient(ENV.EWMS_ADDRESS, token=ENV.EWMS_AUTH)
    LOGGER.info("Connected to EWMS")

    interval_timer = utils.EveryXSeconds(ENV.TMS_OUTER_LOOP_WAIT)

    while True:
        # START(S)
        while args := await next_to_start(ewms_rc):
            ewms_taskforce_attrs = await starter.start(
                schedd_obj,
                utils.is_taskforce_to_be_aborted(ewms_rc, args["taskforce_uuid"]),
                **args,  # TODO
            )
            # confirm start (otherwise ewms will request this one again -- good for statelessness)
            await ewms_rc.request(
                "POST",
                f"/tms/taskforce/running/{args['taskforce_uuid']}",
                ewms_taskforce_attrs,
            )
            LOGGER.info("Sent taskforce info to EWMS")

        #
        # TODO - build out logic to auto-start and/or auto-stop
        #

        # STOP(S)
        while args := await next_to_stop(ewms_rc):
            stopper.stop(
                schedd_obj,
                args["cluster_id"],
            )
            # confirm stop (otherwise ewms will request this one again -- good for statelessness)
            await ewms_rc.request(
                "DELETE",
                f"/tms/taskforce/stop/{args['taskforce_uuid']}",
            )

        # throttle
        while not interval_timer.has_been_x_seconds():
            await asyncio.sleep(1)
