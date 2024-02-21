"""For watching EWMS taskforce workers on an HTCondor cluster."""


import asyncio
import collections
import enum
import json
import logging
import pprint
import time
from pathlib import Path
from typing import Any, AsyncIterator

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import RestClient

from .. import condor_tools as ct
from .. import types, utils
from ..config import ENV, WATCHER_N_TOP_TASK_ERRORS

_ALL_TOP_ERRORS_KEY = "top_task_errors_by_taskforce"
_ALL_COMP_STAT_KEY = "compound_statuses_by_taskforce"


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
                        return f"HELD: {ct.hold_reason_to_string(job_info_val[1], job_info_val[2])}"
                # else -> fall-through

            case _:
                return str(job_info_val)  # who knows what this is

    # keep calm and carry on
    except Exception as e:
        LOGGER.exception(e)

    # fall-through
    return str(job_info_val)


########################################################################################


class UnknownJobEvent(Exception):
    """Raise when the job event is not valid for these purposes."""


class NoUpdateException(Exception):
    """Raise when there is no update to be made."""


########################################################################################


class ClusterInfo:
    """Encapsulates statuses and info of a Condor cluster."""

    def __init__(self, tmonitor: utils.TaskforceMonitor) -> None:
        self.tmonitor = tmonitor
        self.taskforce_uuid = tmonitor.taskforce_uuid
        self.seen_in_jel = False

        self._jobs: dict[int, dict[JobInfoKey, JobInfoVal]] = {}

    def aggregate_compound_statuses(
        self,
    ) -> types.AggregateStatuses:
        """Aggregate jobs using a count of each job status & pilot status pair.

        Return value is in a human-readable format, so do not persist for long.

        ```
            {
                job-status: {
                    pilot-status: count (int)
                    pilot-status: count (int)
                    pilot-status: count (int)
                    ...
                }
                job-status: ...
            }
        ```

        Raises:
            `NoUpdateException` -- if there is no update
        """
        job_pilot_compound_statuses: types.AggregateStatuses = {}

        # get counts of each
        for job_status in set(
            job_info.get(JobInfoKey.JobStatus, None) for job_info in self._jobs.values()
        ):
            # get cluster_info ids that match this job-status
            ids_for_this_job_status = [
                i
                for i, job_info in self._jobs.items()
                if job_info.get(JobInfoKey.JobStatus, None) == job_status
            ]
            # now, get the pilot-statuses for this job-status
            key = job_info_val_to_string(JobInfoKey.JobStatus, job_status)
            job_pilot_compound_statuses[key] = dict(
                collections.Counter(
                    job_info_val_to_string(
                        JobInfoKey.HTChirpEWMSPilotStatus,
                        self._jobs[i].get(JobInfoKey.HTChirpEWMSPilotStatus, None),
                    )
                    for i in ids_for_this_job_status
                )
            )

        LOGGER.debug(
            json.dumps(
                job_pilot_compound_statuses,
                sort_keys=True,  # sort -> deterministic
                ensure_ascii=True,
                indent=4,  # for logging
            )
        )

        # is this an update?
        if self.tmonitor.aggregate_statuses == job_pilot_compound_statuses:
            raise NoUpdateException("compound statuses did not change")
        self.tmonitor.aggregate_statuses = job_pilot_compound_statuses

        if not job_pilot_compound_statuses:
            raise NoUpdateException("compound statuses dict is empty")

        return job_pilot_compound_statuses

    def get_top_task_errors(
        self,
    ) -> types.TopTaskErrors:
        """Aggregate top X errors of jobs.

        Return value is in a human-readable format, so do not persist for long.

        Raises:
            `NoUpdateException` -- if there is no update
        """
        counts = collections.Counter(
            job_info_val_to_string(
                JobInfoKey.HTChirpEWMSPilotError,
                dicto.get(JobInfoKey.HTChirpEWMSPilotError, None),
            )
            for dicto in self._jobs.values()
        )
        counts.pop(None, None)  # remove counts of "no error"
        errors: types.TopTaskErrors = dict(counts.most_common(WATCHER_N_TOP_TASK_ERRORS))  # type: ignore[arg-type]

        # is this an update?
        LOGGER.debug(
            json.dumps(
                errors,
                sort_keys=True,  # sort -> deterministic
                ensure_ascii=True,
                indent=4,  # for logging
            )
        )

        if self.tmonitor.top_task_errors == errors:
            raise NoUpdateException("errors did not change")
        self.tmonitor.top_task_errors = errors

        if not errors:
            raise NoUpdateException("errors dict is empty")

        return errors

    @staticmethod
    def _get_ewms_pilot_chirp_value(
        job_event: htcondor.JobEvent,
    ) -> tuple[JobInfoKey, str]:
        """Parse out the chirp value."""
        if "info" not in job_event:
            raise UnknownJobEvent("no 'info' attribute")
        # ex: "HTChirpEWMSPilotStatus: foo bar baz"
        if not job_event["info"].startswith("HTChirpEWMSPilot"):
            raise UnknownJobEvent(
                f"not a 'HTChirpEWMSPilot*' chirp: {job_event['info']}"
            )
        # parse
        try:
            attr, value = job_event["info"].split(":", maxsplit=1)
            jie = JobInfoKey[attr]
        except (ValueError, KeyError) as e:
            raise UnknownJobEvent(
                f"invalid 'HTChirpEWMSPilot*' chirp: {job_event['info']}"
            ) from e
        return jie, value.strip()

    def _set_job_status(
        self,
        job_event: htcondor.JobEvent,
        jie: JobInfoKey,
        value_code_tuple: JobInfoVal,
    ) -> None:
        if job_event.proc not in self._jobs:
            self._jobs[job_event.proc] = {}
        LOGGER.debug(
            f"new job status: "
            f"cluster={job_event.cluster} / "
            f"proc={job_event.proc} / "
            f"event={job_event.get('EventTypeNumber','?')} ({job_event.type.name}) / "
            f"{jie.name} -> {value_code_tuple}"
        )
        self._jobs[job_event.proc][jie] = value_code_tuple

    def update_from_event(
        self,
        job_event: htcondor.JobEvent,
    ) -> None:
        """Extract the meaningful info from the event for the cluster."""
        self.seen_in_jel = True

        #
        # CHIRP -- pilot status
        if job_event.type == htcondor.JobEventType.GENERIC:
            jie, chirp_value = self._get_ewms_pilot_chirp_value(job_event)
            self._set_job_status(job_event, jie, chirp_value)
        #
        # JOB STATUS
        elif job_status := ct.JOB_EVENT_STATUS_TRANSITIONS.get(job_event.type, None):
            match job_status:
                # get hold reason and use that as value
                case htcondor.JobStatus.HELD:
                    self._set_job_status(
                        job_event,
                        JobInfoKey.JobStatus,
                        (
                            job_status.value,
                            job_event.get("HoldReasonCode", 0),
                            job_event.get("HoldReasonSubCode", 0),
                        ),
                    )
                # any other job status
                case _:
                    self._set_job_status(
                        job_event,
                        JobInfoKey.JobStatus,
                        job_status.value,
                    )
        #
        # OTHER
        else:
            raise UnknownJobEvent(f"not an important event: {job_event.type.name}")


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
        "/tms/taskforces/find",
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


########################################################################################


def is_jel_okay_to_delete(ewms_rc: RestClient, jel_fpath: Path) -> bool:
    """Check all conditions for determining if it is time to delete the jel."""

    def is_file_past_modification_expiry(jel_fpath: Path) -> bool:
        """Return whether the file was last modified longer than the expiry."""
        diff = time.time() - jel_fpath.stat().st_mtime
        yes = diff >= ENV.JOB_EVENT_LOG_MODIFICATION_EXPIRY
        if yes:
            LOGGER.warning(f"Job log file {jel_fpath} has not been updated in {diff}s")
        return yes

    return is_file_past_modification_expiry() and utils.any_taskforces_still_using_jel(
        ewms_rc, jel_fpath
    )


########################################################################################


async def watch_job_event_log(
    jel_fpath: Path,
    ewms_rc: RestClient,
    tmonitors: utils.AppendOnlyList[utils.TaskforceMonitor],
) -> None:
    """Watch over one job event log file, containing multiple taskforces.

    NOTE:
        1. a taskforce is never split among multiple files, it uses only one
        2. if this process crashes, the file will be re-read from the top;
            so, there's no need to track progress.
    """
    LOGGER.info(f"This watcher will read {jel_fpath}")

    cluster_infos: dict[types.ClusterId, ClusterInfo] = {}  # LARGE
    interval_timer = utils.EveryXSeconds(ENV.TMS_WATCHER_INTERVAL)
    jel = htcondor.JobEventLog(str(jel_fpath))

    while True:
        # wait for job log to populate (more)
        while not interval_timer.has_been_x_seconds():
            await asyncio.sleep(1)

        # query for new taskforces, so we wait for any
        #   taskforces/clusters that are late to start by condor
        #   (and are not yet in the job log)
        async for taskforce_uuid, cluster_id in query_for_more_taskforces(
            ewms_rc,
            jel_fpath,
            list(c.taskforce_uuid for c in cluster_infos.values()),
        ):
            cluster_infos[cluster_id] = ClusterInfo(
                utils.TaskforceMonitor(taskforce_uuid, cluster_id)
            )
            tmonitors.append(cluster_infos[cluster_id].tmonitor)

        # get events -- exit when no more events, or took too long
        got_new_events = False
        LOGGER.info(f"Reading events from {jel_fpath}...")
        for job_event in jel.events(stop_after=0):  # 0 -> only get currently available
            await asyncio.sleep(0)  # since htcondor is not async
            got_new_events = True
            # update
            try:
                cluster_infos[job_event.cluster].update_from_event(job_event)
            except KeyError:
                LOGGER.warning(
                    f"Cluster found in job event log does not match any "
                    f"known taskforce ({job_event.cluster}), skipping it"
                )
                continue
            except UnknownJobEvent as e:
                LOGGER.debug(f"error: {e}")
            # check times
            if interval_timer.has_been_x_seconds():
                break

        # endgame check
        if (not got_new_events) and all(c.seen_in_jel for c in cluster_infos.values()):
            if is_jel_okay_to_delete(ewms_rc, jel_fpath):
                jel_fpath.unlink()  # delete file
                LOGGER.warning(f"Deleted job log file {jel_fpath}")
                return
            else:
                continue

        LOGGER.info("Done reading events for now")
        # TODO - remove
        LOGGER.debug(
            pprint.pformat({k: v._jobs for k, v in cluster_infos.items()}, indent=4)
        )

        patch_body: dict[str, Any] = {
            _ALL_TOP_ERRORS_KEY: {},
            _ALL_COMP_STAT_KEY: {},
        }

        # aggregate
        # NOTE: We unfortunately cannot reduce the data after aggregating.
        #  Once we aggregate we lose job-level granularity, which is
        #  needed for replacing/updating individual jobs' status(es).
        #  Alternatively, we could re-parse the entire job log every time.
        for cid, info in cluster_infos.items():
            try:
                LOGGER.info(
                    f"Getting top task errors {info.taskforce_uuid=} / {cid=}..."
                )
                patch_body[_ALL_TOP_ERRORS_KEY][
                    info.taskforce_uuid
                ] = info.get_top_task_errors()
            except NoUpdateException:
                pass
            try:
                LOGGER.info(
                    f"Aggregating compound statuses {info.taskforce_uuid=} / {cid=}..."
                )
                patch_body[_ALL_COMP_STAT_KEY][
                    info.taskforce_uuid
                ] = info.aggregate_compound_statuses()
            except NoUpdateException:
                pass

        # send -- one big update that way it can't intermittently fail
        # (it's okay to send an empty sub-dict, but all empties is pointless)
        if any(patch_body[k] for k in [_ALL_TOP_ERRORS_KEY, _ALL_COMP_STAT_KEY]):
            LOGGER.info("Sending updates to EWMS...")
            await ewms_rc.request(
                "POST",
                "/tms/taskforces/report",
                patch_body,
            )
        else:
            LOGGER.info("No updates needed for EWMS")
