"""Scalar entrypoint."""


import logging
from typing import Any

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import ClientCredentialsAuth, RestClient

from .. import utils
from ..condor_tools import get_collector, get_schedd
from ..config import ENV
from . import starter, stopper

LOGGER = logging.getLogger(__name__)


async def get_next_to_start(ewms_rc: RestClient) -> dict[str, Any]:
    """Get the next taskforce requested for this collector + schedd.

    Returns empty dict when there is no taskforce to start.
    """
    resp = await ewms_rc.request(
        "GET",
        "/taskforce/tms-action/pending-starter",
        {"collector": get_collector(), "schedd": get_schedd()},
    )
    LOGGER.debug(f"NEXT TO START: {resp}")
    return resp  # type: ignore[no-any-return]


async def get_next_to_stop(ewms_rc: RestClient) -> dict[str, Any]:
    """Get the next taskforce requested for this collector + schedd.

    Returns empty dict when there is no taskforce to stop.
    """
    resp = await ewms_rc.request(
        "GET",
        "/taskforce/tms-action/pending-stopper",
        {"collector": get_collector(), "schedd": get_schedd()},
    )
    LOGGER.debug(f"NEXT TO STOP: {resp}")
    return resp  # type: ignore[no-any-return]


async def confirm_start(
    ewms_rc: RestClient,
    taskforce_uuid: str,
    body: dict[str, Any],
) -> None:
    """Send confirmation to EWMS that taskforce was started."""
    await ewms_rc.request(
        "POST",
        f"/taskforce/tms-action/condor-submit/{taskforce_uuid}",
        body,
    )
    LOGGER.info("CONFIRMED TASKFORCE START -- sent taskforce info to EWMS")


async def confirm_stop(ewms_rc: RestClient, taskforce_uuid: str) -> None:
    """Send confirmation to EWMS that taskforce was stopped."""
    await ewms_rc.request(
        "DELETE",
        f"/taskforce/tms-action/pending-stopper/{taskforce_uuid}",
    )
    LOGGER.info("CONFIRMED TASKFORCE STOPPED")


async def scalar_loop(
    tmonitors: utils.AppendOnlyList[utils.TaskforceMonitor],
    # NOTE - ^^^^ can be used for the smart starter/stopper IF this decision is made on TMS.
    #        if the decision is made by the WMS, then this is not needed (I'm leaning toward this)
) -> None:
    """Listen to EWMS and start and/or designated taskforces."""
    LOGGER.info("Starting scalar...")

    # make connections -- do now so we don't have any surprises downstream
    LOGGER.info("Connecting to HTCondor...")
    schedd_obj = htcondor.Schedd()  # no auth need b/c we're on AP
    LOGGER.info("Connecting to EWMS...")
    ewms_rc = ClientCredentialsAuth(
        ENV.EWMS_ADDRESS,
        ENV.EWMS_TOKEN_URL,
        ENV.EWMS_CLIENT_ID,
        ENV.EWMS_CLIENT_SECRET,
    )

    interval_timer = utils.EveryXSeconds(ENV.TMS_OUTER_LOOP_WAIT)

    while True:
        LOGGER.info("Activating starter...")
        # START(S)
        while ewms_pending_starter_attrs := await get_next_to_start(ewms_rc):
            try:
                ewms_condor_submit_attrs = await starter.start(
                    schedd_obj,
                    ewms_rc,
                    #
                    ewms_pending_starter_attrs["taskforce_uuid"],
                    ewms_pending_starter_attrs["n_workers"],
                    #
                    **ewms_pending_starter_attrs["container_config"],
                    #
                    **ewms_pending_starter_attrs["worker_config"],
                )
            except starter.TaskforceNoLongerPendingStarter:
                continue
            # confirm start (otherwise ewms will request this one again -- good for statelessness)
            await confirm_start(
                ewms_rc,
                ewms_pending_starter_attrs["taskforce_uuid"],
                ewms_condor_submit_attrs,
            )
        LOGGER.info("De-activated starter.")

        # STOP(S)
        LOGGER.info("Activating stopper...")
        while ewms_pending_starter_attrs := await get_next_to_stop(ewms_rc):
            stopper.stop(
                schedd_obj,
                ewms_pending_starter_attrs["cluster_id"],
            )
            # confirm stop (otherwise ewms will request this one again -- good for statelessness)
            await confirm_stop(
                ewms_rc,
                ewms_pending_starter_attrs["taskforce_uuid"],
            )
        LOGGER.info("De-activated stopper.")

        # throttle
        await interval_timer.wait_until_x(LOGGER)
