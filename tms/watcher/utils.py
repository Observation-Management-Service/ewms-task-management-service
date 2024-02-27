"""utils.py."""


import enum
import logging
import time
from pathlib import Path
from typing import AsyncIterator

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import RestClient

from .. import condor_tools, types
from ..config import ENV

LOGGER = logging.getLogger(__name__)


########################################################################################


JobInfoVal = tuple[int, ...] | str


class JobInfoKey(enum.Enum):
    """Represent important job attributes while minimizing memory.

    NOTE - enum members are singletons -> good for memory reduction
    """

    # pylint:disable=invalid-name

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
    LOGGER.info("Querying for more taskforces from EWMS...")
    res = await ewms_rc.request(
        "POST",
        "/taskforces/find",
        {
            "filter": {
                "collector": ENV.COLLECTOR,
                "schedd": ENV.SCHEDD,
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


async def any_taskforces_still_using_jel(
    ewms_rc: RestClient,
    jel_fpath: Path,
) -> bool:
    """Return whether there are non-completed taskforces using the JEL."""
    resp = await ewms_rc.request(
        "POST",
        "/taskforces/find",
        {
            "query": {
                "job_event_log_fpath": str(jel_fpath),
                "collector": ENV.COLLECTOR,
                "schedd": ENV.SCHEDD,
                "condor_complete_ts": {"$ne": None},
            },
            "projection": ["taskforce_uuid"],
        },
    )
    return len(resp["taskforces"]) != 0


async def send_condor_complete(
    ewms_rc: RestClient,
    taskforce_uuid: str,
    timestamp: int,
) -> None:
    """Tell EWMS that this taskforce is condor-complete."""
    await ewms_rc.request(
        "POST",
        f"/taskforce/tms/condor-complete/{taskforce_uuid}",
        {
            "condor_complete_ts": timestamp,
        },
    )


async def is_jel_okay_to_delete(ewms_rc: RestClient, jel_fpath: Path) -> bool:
    """Check all conditions for determining if it is time to delete the JEL."""

    def is_file_past_modification_expiry() -> bool:
        """Return whether the file was last modified longer than the expiry."""
        diff = time.time() - jel_fpath.stat().st_mtime
        yes = diff >= ENV.JOB_EVENT_LOG_MODIFICATION_EXPIRY
        if yes:
            LOGGER.warning(f"JEL file {jel_fpath} has not been updated in {diff}s")
        return yes

    return is_file_past_modification_expiry() and await any_taskforces_still_using_jel(
        ewms_rc, jel_fpath
    )
