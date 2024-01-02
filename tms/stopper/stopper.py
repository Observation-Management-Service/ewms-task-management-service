"""For stopping Skymap Scanner clients on an HTCondor cluster."""


import logging

import htcondor  # type: ignore[import-untyped]

from ..config import ENV

LOGGER = logging.getLogger(__name__)


def stop(cluster_id: str) -> None:
    """Main logic."""
    LOGGER.info(
        f"Stopping Skymap Scanner client workers on {cluster_id} / {ENV.COLLECTOR} / {ENV.SCHEDD}"
    )

    schedd_obj = htcondor.Schedd()

    # Remove workers -- may not be instantaneous
    LOGGER.info("Requesting removal...")
    act_obj = schedd_obj.act(
        htcondor.JobAction.Remove,
        f"ClusterId == {cluster_id}",
        reason="Requested by SkyDriver",
    )
    LOGGER.debug(act_obj)
    LOGGER.info(f"Removed {act_obj['TotalSuccess']} workers")
