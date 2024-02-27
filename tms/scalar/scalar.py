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
    """Get the next taskforce requested for this collector + schedd.

    Returns empty dict when there is no taskforce to start.
    """
    return await ewms_rc.request(  # type: ignore[no-any-return]
        "GET",
        "/taskforce/tms-action/pending-starter",
        {"collector": ENV.COLLECTOR, "schedd": ENV.SCHEDD},
    )


async def next_to_stop(ewms_rc: RestClient) -> dict[str, Any]:
    """Get the next taskforce requested for this collector + schedd.

    Returns empty dict when there is no taskforce to stop.
    """
    return await ewms_rc.request(  # type: ignore[no-any-return]
        "GET",
        "/taskforce/tms-action/pending-stopper",
        {"collector": ENV.COLLECTOR, "schedd": ENV.SCHEDD},
    )


async def scalar_loop(
    tmonitors: utils.AppendOnlyList[utils.TaskforceMonitor],
    # NOTE - ^^^^ can be used for the smart starter/stopper IF this decision is made on TMS.
    #        if the decision is made by the WMS, then this is not needed (I'm leaning toward this)
) -> None:
    """Listen to EWMS and start and/or designated taskforces."""

    # make connections -- do now so we don't have any surprises downstream
    schedd_obj = htcondor.Schedd()  # no auth need b/c we're on AP
    ewms_rc = RestClient(ENV.EWMS_ADDRESS, token=ENV.EWMS_AUTH)
    LOGGER.info("Connected to EWMS")

    interval_timer = utils.EveryXSeconds(ENV.TMS_OUTER_LOOP_WAIT)

    while True:
        # START(S)
        while ewms_pending_starter_attrs := await next_to_start(ewms_rc):
            try:
                ewms_condor_submit_attrs = await starter.start(
                    schedd_obj,
                    utils.is_taskforce_still_pending_starter(
                        ewms_rc, ewms_pending_starter_attrs["taskforce_uuid"]
                    ),
                    #
                    ewms_pending_starter_attrs["taskforce_uuid"],
                    ewms_pending_starter_attrs["n_workers"],
                    #
                    **ewms_pending_starter_attrs["taskforce_args"],
                    #
                    **ewms_pending_starter_attrs["condor_args"],
                )
            except starter.TaskforceNoLongerPendingStarter:
                continue
            # confirm start (otherwise ewms will request this one again -- good for statelessness)
            await ewms_rc.request(
                "POST",
                f"/taskforce/tms-action/condor-submit/{ewms_pending_starter_attrs['taskforce_uuid']}",
                ewms_condor_submit_attrs,
            )
            LOGGER.info("Sent taskforce info to EWMS")

        #
        # TODO - build out logic to auto-start and/or auto-stop
        #

        # STOP(S)
        while ewms_pending_starter_attrs := await next_to_stop(ewms_rc):
            stopper.stop(
                schedd_obj,
                ewms_pending_starter_attrs["cluster_id"],
            )
            # confirm stop (otherwise ewms will request this one again -- good for statelessness)
            await ewms_rc.request(
                "DELETE",
                f"/taskforce/tms-action/pending-stopper/{ewms_pending_starter_attrs['taskforce_uuid']}",
            )

        # throttle
        while not interval_timer.has_been_x_seconds():
            await asyncio.sleep(1)
