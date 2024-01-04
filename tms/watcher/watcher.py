"""For watching EWMS taskforce workers on an HTCondor cluster."""


import asyncio
import collections
import enum
import logging
import time
from pathlib import Path

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import RestClient

from .. import condor_tools as ct
from ..config import ENV, WATCHER_INTERVAL, WATCHER_N_TOP_TASK_ERRORS

LOGGER = logging.getLogger(__name__)


class JobInfoEnum(enum.Enum):
    """Represent important job attributes while minimizing memory."""

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


class UnknownJobEvent(Exception):
    """Raise when the job event is not valid for these purposes."""


class NoUpdateException(Exception):
    """Raise when there is no update to be made."""


class ClusterInfo:
    """Encapsulates statuses and info of a Condor cluster."""

    def __init__(self) -> None:
        self._jobs: dict[int, dict[int, str]] = {}
        self._previous_aggregate_statuses: dict[str | None, dict[str | None, int]] = {}
        self._previous_top_task_errors: dict[str, int] = {}

    def aggregate_statuses(
        self,
    ) -> dict[str | None, dict[str | None, int]]:
        """Aggregate statuses of jobs.

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

        # pre-allocate statuses as keys
        statuses: dict[str | None, dict[str | None, int]] = {
            k: {}
            for k in set(
                info.get(JobInfoEnum.JobStatus.value, None)
                for info in self._jobs.values()
            )
        }

        # get counts of each
        for job_status in statuses:
            # get cluster_info ids that match this status
            ids_for_this_job_status = [
                i
                for i, info in self._jobs.items()
                if info.get(JobInfoEnum.JobStatus.value, None) == job_status
            ]
            # now, get the pilot-statuses for this job-status
            statuses[job_status] = dict(
                collections.Counter(
                    self._jobs[i].get(JobInfoEnum.HTChirpEWMSPilotStatus.value, None)
                    for i in ids_for_this_job_status
                )
            )

        # validate & return
        if statuses == self._previous_aggregate_statuses:
            raise NoUpdateException()
        self._previous_aggregate_statuses = statuses
        return self._previous_aggregate_statuses

    def get_top_task_errors(
        self,
    ) -> dict[str, int]:
        """Aggregate top X errors of jobs.

        Raises:
            `NoUpdateException` -- if there is no update
        """
        counts = collections.Counter(
            dicto.get(JobInfoEnum.HTChirpEWMSPilotError.value, None)
            for dicto in self._jobs.values()
        )
        counts.pop(None, None)  # remove counts of "no error"

        errors = dict(counts.most_common(WATCHER_N_TOP_TASK_ERRORS))

        # validate & return
        if errors == self._previous_top_task_errors:
            raise NoUpdateException()
        self._previous_top_task_errors = errors  # type: ignore[assignment]
        return self._previous_top_task_errors

    def update_from_event(
        self,
        job_event: htcondor.JobEvent,
    ) -> None:
        """Extract the meaningful info from the event for the cluster."""
        #
        # CHIRP -- pilot status
        if job_event.type == htcondor.JobEvent.GENERIC:
            if "info" not in job_event:
                raise UnknownJobEvent("no 'info' atribute")
            # ex: "HTChirpEWMSPilotStatus: foo bar baz"
            if not job_event["info"].startswith("HTChirpEWMSPilot"):
                raise UnknownJobEvent("not a 'HTChirpEWMSPilot*' chirp")
            # parse
            try:
                attr, value = job_event["info"].split(":", maxsplit=1)
                jie = JobInfoEnum[attr]
            except (ValueError, KeyError) as e:
                raise UnknownJobEvent(
                    f"invalid 'HTChirpEWMSPilot*' chirp: {job_event['info']}"
                ) from e
            self._jobs[job_event.proc][jie.value] = value.strip()
        #
        # JOB STATUS
        elif job_status := ct.JOB_EVENT_STATUS_TRANSITIONS.get(job_event.type, None):
            jie = JobInfoEnum.JobStatus
            # TODO -- get hold reason and use that as value
            self._jobs[job_event.proc][jie.value] = job_status.name  # str
        #
        # OTHER
        else:
            raise UnknownJobEvent(f"not an important event: {job_event.type.name}")


class EveryXSeconds:
    """Keep track of durations."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self._last_time = time.time()

    def has_been_x_seconds(self) -> bool:
        """Has it been at least `self.seconds` since last time?"""
        diff = time.time() - self._last_time
        yes = diff >= self.seconds
        if yes:
            self._last_time = time.time()
            LOGGER.info(f"has been at least {self.seconds}s (actually {diff}s)")
        return yes


async def watch_job_event_log(jel_fpath: Path) -> None:
    """Watch over one job event log file, containing multiple taskforces.

    NOTE -- a taskforce is never split among multiple files, it uses only one
    """
    LOGGER.info(f"This watcher will read {jel_fpath}")

    # make connections -- do now so we don't have any surprises downstream
    ewms_rc = RestClient(ENV.EWMS_ADDRESS, token=ENV.EWMS_AUTH)
    LOGGER.info("Connected to EWMS")

    cluster_info_dict: dict[str, ClusterInfo] = {}  # LARGE

    time_tracker = EveryXSeconds(WATCHER_INTERVAL)

    jel = htcondor.JobEventLog(str(jel_fpath))
    jel_index = -1

    while True:
        # wait for job log to populate (more)
        while not time_tracker.has_been_x_seconds():
            await asyncio.sleep(1)

        # get events -- exit when no more events, or took too long
        LOGGER.info(f"Reading events from {jel_fpath}...")
        for job_event in jel.events(stop_after=0):  # 0 -> only get currently available
            jel_index += 1
            if job_event.cluster not in cluster_info_dict:
                cluster_info_dict[job_event.cluster] = ClusterInfo()
            try:
                cluster_info_dict[job_event.cluster].update_from_event(job_event)
            except UnknownJobEvent as e:
                LOGGER.exception(e)
            if time_tracker.has_been_x_seconds():
                break
            await asyncio.sleep(0)  # since htcondor is not async

        LOGGER.info("Done reading events for now")

        # NOTE: We unfortunately cannot reduce the data after aggregating.
        #  Once we aggregate we lose job-level granularity, which is
        #  needed for replacing/updating individual jobs' status(es).
        #  Alternatively, we could re-parse the entire job log every time.

        # aggregate
        LOGGER.info("Getting top task errors...")
        top_task_errors_by_cluster = {}
        for cluster_id, info in cluster_info_dict.items():
            try:
                top_task_errors_by_cluster[cluster_id] = info.get_top_task_errors()
            except NoUpdateException:
                pass
        LOGGER.info("Aggregating job statuses...")
        statuses_by_cluster = {}
        for cluster_id, info in cluster_info_dict.items():
            try:
                statuses_by_cluster[cluster_id] = info.aggregate_statuses()
            except NoUpdateException:
                pass

        # send -- one big update that way it won't intermittently fail
        if top_task_errors_by_cluster or statuses_by_cluster:
            LOGGER.info("Sending updates to EWMS...")
            LOGGER.debug(top_task_errors_by_cluster)
            LOGGER.debug(statuses_by_cluster)
            await ewms_rc.request(
                "PATCH",
                "/condor-cluster/many",
                {
                    # we don't have the taskforce_uuid(s), but...
                    # EWMS can map (collector + schedd + condor_id) to a taskforce_uuid
                    "collector": ENV.COLLECTOR,
                    "schedd": ENV.SCHEDD,
                    "jel_index": jel_index,
                    "top_task_errors_by_cluster": top_task_errors_by_cluster,
                    "statuses_by_cluster": statuses_by_cluster,
                },
            )
        else:
            LOGGER.info("No updates needed for EWMS")

    # TODO -- delete file
