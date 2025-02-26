"""For stopping EWMS taskforce workers on an HTCondor cluster."""

import logging

import htcondor  # type: ignore[import-untyped]

from .. import types
from ..condor_tools import get_collector, get_schedd

LOGGER = logging.getLogger(__name__)


def stop(
    schedd_obj: htcondor.Schedd,
    #
    cluster_id: types.ClusterId,
) -> None:
    """Main logic."""
    LOGGER.info(
        f"Stopping EWMS taskforce workers on {cluster_id} / {get_collector()} / {get_schedd()}"
    )

    # Remove workers -- may not be instantaneous
    act_obj = schedd_obj.act(
        htcondor.JobAction.Remove,
        f"ClusterId == {cluster_id}",
        reason="Requested by EWMS",
    )
    LOGGER.debug(act_obj)
    LOGGER.info(f"Removed {act_obj['TotalSuccess']} workers")
