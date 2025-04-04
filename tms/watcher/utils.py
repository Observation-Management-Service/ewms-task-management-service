"""utils.py."""

import enum
import logging
import time
from pathlib import Path
from typing import AsyncIterator

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import RestClient

from .. import condor_tools, types
from ..condor_tools import get_collector, get_schedd
from ..config import ENV, WMS_URL_V_PREFIX

LOGGER = logging.getLogger(__name__)


########################################################################################


JobInfoVal = tuple[int, ...] | str


class JobInfoKey(enum.Enum):
    """Represent important job attributes while minimizing memory.

    NOTE - enum members are singletons -> good for memory reduction
    """

    ClusterId = enum.auto()
    JobStatus = enum.auto()
    EnteredCurrentStatus = enum.auto()
    ProcId = enum.auto()
    #
    HoldReason = enum.auto()
    HoldReasonCode = enum.auto()
    HoldReasonSubCode = enum.auto()
    #
    HTChirpEWMSPilotLastUpdatedTimestamp = enum.auto()
    HTChirpEWMSPilotStartedTimestamp = enum.auto()
    HTChirpEWMSPilotStatus = enum.auto()
    #
    HTChirpEWMSPilotTasksTotal = enum.auto()
    HTChirpEWMSPilotTasksFailed = enum.auto()
    HTChirpEWMSPilotTasksSuccess = enum.auto()
    #
    HTChirpEWMSPilotError = enum.auto()
    HTChirpEWMSPilotErrorTraceback = enum.auto()


def job_info_val_to_string(
    job_info_key: JobInfoKey,
    job_info_val: JobInfoVal | None,
) -> str | None:
    """Convert the JobInfoVal instance to a string (or None).

    This will increase memory, so do not persist return value for long.
    """
    if job_info_val is None:
        return None

    try:
        match job_info_key:
            case JobInfoKey.HTChirpEWMSPilotError:
                return str(job_info_val)  # *should* already be a str

            case JobInfoKey.JobStatus:
                if isinstance(job_info_val, int):
                    return str(htcondor.JobStatus(job_info_val).name)
                elif isinstance(job_info_val, tuple):
                    if job_info_val[0] == htcondor.JobStatus.HELD:
                        return f"HELD: {condor_tools.hold_reason_to_string(job_info_val[1], job_info_val[2])}"
                # else -> fall-through

            case _:
                return str(job_info_val)  # who knows what this is

    # keep calm and carry on
    except Exception as e:
        LOGGER.exception(e)

    # fall-through
    return str(job_info_val)


########################################################################################


async def query_for_more_taskforces(
    ewms_rc: RestClient,
    jel_fpath: Path,
    taskforce_uuids: list[str],
) -> AsyncIterator[tuple[str, types.ClusterId]]:
    """Get new taskforce uuids."""
    LOGGER.debug("Querying for more taskforces from EWMS...")
    res = await ewms_rc.request(
        "POST",
        f"/{WMS_URL_V_PREFIX}/query/taskforces",
        {
            "query": {
                "collector": get_collector(),
                "schedd": get_schedd(),
                "job_event_log_fpath": str(jel_fpath),
            },
            "projection": ["taskforce_uuid", "cluster_id"],
        },
    )
    for dicto in res["taskforces"]:
        if dicto["taskforce_uuid"] in taskforce_uuids:
            continue
        LOGGER.info(f"Tracking new taskforce: {dicto}")
        yield dicto["taskforce_uuid"], dicto["cluster_id"]


async def send_condor_complete(
    ewms_rc: RestClient,
    taskforce_uuid: str,
    timestamp: int,
) -> None:
    """Tell EWMS that this taskforce is condor-complete."""
    await ewms_rc.request(
        "POST",
        f"/{WMS_URL_V_PREFIX}/tms/condor-complete/taskforces/{taskforce_uuid}",
        {
            "condor_complete_ts": timestamp,
        },
    )


async def is_jel_okay_to_delete(ewms_rc: RestClient, jel_fpath: Path) -> bool:
    """Check all conditions for determining if it is time to delete the JEL."""

    def is_jel_past_modification_expiry() -> bool:
        """Return whether the time since last mod is longer than the expiry."""
        diff = time.time() - jel_fpath.stat().st_mtime
        yes = diff >= ENV.JOB_EVENT_LOG_MODIFICATION_EXPIRY
        if yes:
            LOGGER.warning(f"JEL file {jel_fpath} has not been updated in {diff}s")
        return yes

    async def is_jel_no_longer_used() -> bool:
        """Return whether there are no non-completed taskforces using JEL."""
        resp = await ewms_rc.request(
            "POST",
            f"/{WMS_URL_V_PREFIX}/query/taskforces",
            {
                "query": {
                    "job_event_log_fpath": str(jel_fpath),
                    "collector": get_collector(),
                    "schedd": get_schedd(),
                    "condor_complete_ts": {"$ne": None},
                },
                "projection": ["taskforce_uuid"],
            },
        )
        if is_used := bool(resp["taskforces"]):
            LOGGER.info(
                "There are still non-completed taskforces using JEL -- DON'T DELETE"
            )
        else:
            LOGGER.warning(
                "There are no non-completed taskforces using JEL -- CAN DELETE"
            )
        return not is_used

    return is_jel_past_modification_expiry() and await is_jel_no_longer_used()
