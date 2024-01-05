"""General Utilities."""


import logging

from rest_tools.client import RestClient

LOGGER = logging.getLogger(__name__)


async def is_taskforce_to_be_aborted(ewms_rc: RestClient, taskforce_uuid: str) -> bool:
    """Return whether the taskforce has been signaled for removal."""
    ret = await ewms_rc.request(
        "GET",
        f"/tms/taskforce/{taskforce_uuid}",
    )
    return ret["is_deleted"]  # type: ignore[no-any-return]
