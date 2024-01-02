"""General Utilities."""


import logging
from typing import Any

from rest_tools.client import RestClient

from .config import ENV

LOGGER = logging.getLogger(__name__)


def connect_to_ewms() -> RestClient:
    """Connect to EWMS REST server."""
    ewms_rc = RestClient(
        ENV.EWMS_ADDRESS,
        token=ENV.EWMS_AUTH,
    )

    LOGGER.info("Connected to EWMS")
    return ewms_rc


def ewms_aborted_taskforce(ewms_rc: RestClient, taskforce_uuid: str) -> bool:
    """Return whether the taskforce has been signaled for removal."""
    ret = ewms_rc.request_seq(
        "GET",
        f"/taskforce/{taskforce_uuid}",
    )
    return ret["is_deleted"]  # type: ignore[no-any-return]


def update_ewms_taskforce(
    ewms_rc: RestClient,
    taskforce_uuid: str,
    patch_attrs: dict[str, Any],
) -> None:
    """Send EWMS updates from the `submit_result`."""
    if not patch_attrs:
        return

    ewms_rc.request_seq(
        "PATCH",
        f"/taskforce/{taskforce_uuid}",
        patch_attrs,
    )
