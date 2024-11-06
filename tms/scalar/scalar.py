"""Scalar entrypoint."""

import asyncio
import json
import logging
from typing import Any

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import ClientCredentialsAuth, RestClient

from . import starter, stopper
from .. import utils
from ..condor_tools import get_collector, get_schedd
from ..config import ENV, WMS_ROUTE_VERSION_PREFIX

LOGGER = logging.getLogger(__name__)


########################################################################################
# Helper functions


class EWMSCaller:
    """Several REST calls to EWMS."""

    @staticmethod
    async def get_next_to_start(ewms_rc: RestClient) -> dict[str, Any] | None:
        """Get the next taskforce requested for this collector + schedd.

        Returns 'None' when there is no taskforce to start.
        """
        resp = await ewms_rc.request(
            "GET",
            f"/{WMS_ROUTE_VERSION_PREFIX}/tms/pending-starter/taskforces",
            {"collector": get_collector(), "schedd": get_schedd()},
        )
        if not resp:
            return None
        LOGGER.debug(f"NEXT TO START: {resp}")

        def envjson(enviro: dict) -> str:
            """Convert the env dict to a json string unless it's empty."""
            if not enviro:
                return ""
            return json.dumps(enviro)

        # inject task-related attrs into 'environment' dict
        resp["taskforce"]["pilot_config"]["environment"].update(
            {
                "EWMS_PILOT_TASK_IMAGE": resp["task_directive"]["task_image"],
                "EWMS_PILOT_TASK_ARGS": resp["task_directive"]["task_args"],
                "EWMS_PILOT_TASK_ENV_JSON": envjson(resp["task_directive"]["task_env"]),
                "EWMS_PILOT_INIT_IMAGE": resp["task_directive"]["init_image"],
                "EWMS_PILOT_INIT_ARGS": resp["task_directive"]["init_args"],
                "EWMS_PILOT_INIT_ENV_JSON": envjson(resp["task_directive"]["init_env"]),
            }
        )

        def append_to_delim_str(_existing_val: str | None, _val: str) -> str:
            """Append the new value with `;`-delimiter, ensuring no leading `;` if empty."""
            if _existing_val:
                return f"{_existing_val};{_val}"
            else:
                return _val

        # inject mq-related attrs into 'environment' dict
        for mqprofile in resp["mqprofiles"]:
            environment = resp["taskforce"]["pilot_config"]["environment"]
            mqid = mqprofile["mqid"]
            auth_token = mqprofile["auth_token"]
            broker_type = mqprofile["broker_type"]
            broker_address = mqprofile["broker_address"]

            # NOTE: these two conditions are not mutually exclusive, think: self loop (recursive)
            # INCOMING QUEUE(S)
            if mqid in resp["task_directive"]["input_queues"]:
                attr_vals = {
                    "EWMS_PILOT_QUEUE_INCOMING": mqid,
                    "EWMS_PILOT_QUEUE_INCOMING_AUTH_TOKEN": auth_token,
                    "EWMS_PILOT_QUEUE_INCOMING_BROKER_TYPE": broker_type,
                    "EWMS_PILOT_QUEUE_INCOMING_BROKER_ADDRESS": broker_address,
                }
                for attr, val in attr_vals.items():
                    environment[attr] = append_to_delim_str(environment.get(attr), val)
            # OUTGOING QUEUE(S)
            # NOTE: not an *elif*, see note above
            if mqid in resp["task_directive"]["output_queues"]:
                attr_vals = {
                    "EWMS_PILOT_QUEUE_OUTGOING": mqid,
                    "EWMS_PILOT_QUEUE_OUTGOING_AUTH_TOKEN": auth_token,
                    "EWMS_PILOT_QUEUE_OUTGOING_BROKER_TYPE": broker_type,
                    "EWMS_PILOT_QUEUE_OUTGOING_BROKER_ADDRESS": broker_address,
                }
                for attr, val in attr_vals.items():
                    environment[attr] = append_to_delim_str(environment.get(attr), val)

        return resp["taskforce"]  # type: ignore[no-any-return]

    @staticmethod
    async def get_next_to_stop(ewms_rc: RestClient) -> dict[str, Any] | None:
        """Get the next taskforce requested for this collector + schedd.

        Returns 'None' when there is no taskforce to stop.
        """
        resp = await ewms_rc.request(
            "GET",
            f"/{WMS_ROUTE_VERSION_PREFIX}/tms/pending-stopper/taskforces",
            {"collector": get_collector(), "schedd": get_schedd()},
        )
        if not resp:
            return None
        LOGGER.debug(f"NEXT TO STOP: {resp}")

        return resp  # type: ignore[no-any-return]

    @staticmethod
    async def confirm_condor_submit(
        ewms_rc: RestClient,
        taskforce_uuid: str,
        body: dict[str, Any],
    ) -> None:
        """Send confirmation to EWMS that taskforce was started."""
        await ewms_rc.request(
            "POST",
            f"/{WMS_ROUTE_VERSION_PREFIX}/tms/condor-submit/taskforces/{taskforce_uuid}",
            body,
        )
        LOGGER.info("CONFIRMED TASKFORCE START -- sent taskforce info to EWMS")

    @staticmethod
    async def notify_failed_condor_submit(
        ewms_rc: RestClient,
        taskforce_uuid: str,
        error: str,
    ) -> None:
        """Send notification to EWMS that taskforce failed to start."""
        await ewms_rc.request(
            "POST",
            f"/{WMS_ROUTE_VERSION_PREFIX}/tms/condor-submit/taskforces/{taskforce_uuid}/failed",
            {"error": error},
        )
        LOGGER.info(f"NOTIFIED EWMS THAT TASKFORCE FAILED TO START -- {error}")

    @staticmethod
    async def confirm_condor_rm(
        ewms_rc: RestClient,
        taskforce_uuid: str,
    ) -> None:
        """Send confirmation to EWMS that taskforce was stopped."""
        await ewms_rc.request(
            "POST",
            f"/{WMS_ROUTE_VERSION_PREFIX}/tms/condor-rm/taskforces/{taskforce_uuid}",
        )
        LOGGER.info("CONFIRMED TASKFORCE STOPPED")

    @staticmethod
    async def notify_failed_condor_rm(
        ewms_rc: RestClient,
        taskforce_uuid: str,
        error: str,
    ) -> None:
        """Send notification to EWMS that taskforce failed to stop."""
        await ewms_rc.request(
            "POST",
            f"/{WMS_ROUTE_VERSION_PREFIX}/tms/condor-rm/taskforces/{taskforce_uuid}/failed",
        )
        LOGGER.info(f"NOTIFIED EWMS THAT TASKFORCE FAILED TO STOP -- {error}")


########################################################################################
# Loops


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
        # START(S)
        LOGGER.debug("Activating starter...")
        await start_all(schedd_obj, ewms_rc)
        LOGGER.debug("De-activated starter.")

        # STOP(S)
        LOGGER.debug("Activating stopper...")
        await stop_all(schedd_obj, ewms_rc)
        LOGGER.debug("De-activated stopper.")

        # throttle
        await interval_timer.wait_until_x(LOGGER)


async def start_all(
    schedd_obj: htcondor.Schedd,
    ewms_rc: RestClient,
) -> None:
    """Invoke the starter on every designated taskforce."""
    while ewms_pending_starter_attrs := await EWMSCaller.get_next_to_start(ewms_rc):
        try:
            ewms_condor_submit_attrs = await starter.start(
                schedd_obj,
                ewms_rc,
                #
                ewms_pending_starter_attrs["taskforce_uuid"],
                ewms_pending_starter_attrs["n_workers"],
                #
                ewms_pending_starter_attrs["pilot_config"],
                #
                ewms_pending_starter_attrs["worker_config"],
            )
        except starter.TaskforceNotToBeStarted:
            continue  # do not sleep, ask for next TF
        except htcondor.HTCondorInternalError as e:
            LOGGER.error(e)
            await EWMSCaller.notify_failed_condor_submit(
                ewms_rc,
                ewms_pending_starter_attrs["taskforce_uuid"],
                str(e),
            )
            await asyncio.sleep(ENV.TMS_ERROR_WAIT)
            continue  # ask for next TF
        else:
            # confirm start (otherwise tms will pull this one again -- good for statelessness)
            await EWMSCaller.confirm_condor_submit(
                ewms_rc,
                ewms_pending_starter_attrs["taskforce_uuid"],
                ewms_condor_submit_attrs,
            )


async def stop_all(
    schedd_obj: htcondor.Schedd,
    ewms_rc: RestClient,
) -> None:
    """Invoke the stopper on every designated taskforce."""
    while ewms_pending_stopper_attrs := await EWMSCaller.get_next_to_stop(ewms_rc):
        try:
            stopper.stop(
                schedd_obj,
                ewms_pending_stopper_attrs["cluster_id"],
            )
        except htcondor.HTCondorInternalError as e:
            LOGGER.error(e)
            await EWMSCaller.notify_failed_condor_rm(
                ewms_rc,
                ewms_pending_stopper_attrs["taskforce_uuid"],
                str(e),
            )
            await asyncio.sleep(ENV.TMS_ERROR_WAIT)
            continue  # ask for next TF
        else:
            # confirm stop (otherwise ewms will request this one again -- good for statelessness)
            await EWMSCaller.confirm_condor_rm(
                ewms_rc,
                ewms_pending_stopper_attrs["taskforce_uuid"],
            )
