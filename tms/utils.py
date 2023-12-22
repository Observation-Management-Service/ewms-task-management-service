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
    scan_id: str,
    #
    orchestrator: str,
    location: dict[str, str],
    uuid: str,
    cluster_id: str | int,
    n_workers: int,
    starter_info: dict[str, Any],
    #
    statuses: dict[str, dict[str, int]] | None = None,
    top_task_errors: dict[str, int] | None = None,
) -> None:
    """Send SkyDriver updates from the `submit_result`."""
    skydriver_cluster_obj = {
        "orchestrator": orchestrator,
        "location": location,
        "uuid": uuid,
        "cluster_id": str(cluster_id),
        "n_workers": n_workers,
        "starter_info": starter_info,
    }
    if statuses:
        skydriver_cluster_obj["statuses"] = statuses
    if top_task_errors:
        skydriver_cluster_obj["top_task_errors"] = top_task_errors

    skydriver_rc.request_seq(
        "PATCH",
        f"/scan/{scan_id}/manifest",
        {"cluster": skydriver_cluster_obj},
    )
