"""utils.py."""


import logging

from rest_tools.client import RestClient

LOGGER = logging.getLogger(__name__)


async def send_condor_complete(
    ewms_rc: RestClient,
    taskforce_uuid: str,
    timestamp: int,
) -> None:
    """Tell EWMS that this taskforce is condor-complete."""
    await ewms_rc.request(
        "POST",
        f"/tms/taskforce/condor-complete/{taskforce_uuid}",
        {
            "condor_complete_ts": timestamp,
        },
    )
