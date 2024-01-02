"""General Utilities."""


import logging
from typing import Any

from rest_tools.client import RestClient

from .config import ENV

LOGGER = logging.getLogger(__name__)


def connect_to_skydriver() -> RestClient:
    """Connect to SkyDriver REST server & check scan id."""
    skydriver_rc = RestClient(
        ENV.SKYDRIVER_ADDRESS,
        token=ENV.SKYDRIVER_AUTH,
    )

    LOGGER.info("Connected to SkyDriver")
    return skydriver_rc


def skydriver_aborted_scan(skydriver_rc: RestClient, scan_id: str) -> bool:
    """Return whether the scan has been signaled for deletion."""
    ret = skydriver_rc.request_seq(
        "GET",
        f"/scan/{scan_id}/manifest",
    )
    return ret["is_deleted"]  # type: ignore[no-any-return]


def update_skydriver(
    skydriver_rc: RestClient,
    taskforce_uuid: str,
    patch_attrs: dict[str, Any],
) -> None:
    """Send SkyDriver updates from the `submit_result`."""
    if not patch_attrs:
        return

    skydriver_rc.request_seq(
        "PATCH",
        f"/taskforce/{taskforce_uuid}",
        patch_attrs,
    )
