"""For watching EWMS taskforce workers on an HTCondor cluster."""


import asyncio
import collections
import logging
import time
from pathlib import Path
from typing import Any

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import RestClient

from .. import condor_tools as ct
from ..config import ENV, WATCHER_INTERVAL, WATCHER_N_TOP_TASK_ERRORS

LOGGER = logging.getLogger(__name__)


PROJECTION = [
    "ClusterId",
    "JobStatus",
    "EnteredCurrentStatus",
    "ProcId",
    #
    "HoldReason",
    "HoldReasonCode",
    "HoldReasonSubCode",
    #
    "HTChirpEWMSPilotLastUpdatedTimestamp",
    "HTChirpEWMSPilotStartedTimestamp",
    "HTChirpEWMSPilotStatus",
    #
    "HTChirpEWMSPilotTasksTotal",
    "HTChirpEWMSPilotTasksFailed",
    "HTChirpEWMSPilotTasksSuccess",
    #
    "HTChirpEWMSPilotError",
    "HTChirpEWMSPilotErrorTraceback",
]


DONE_JOB_STATUSES: list[int] = [
    ct.REMOVED,
    ct.COMPLETED,
    ct.HELD,
]
NON_RESPONSE_LIMIT = 10


class UnknownEvent(Exception):
    """Raise when the job event is not valid for these purposes."""


class NoUpdateException(Exception):
    """Raise when there is no update to be made."""


class ClusterInfo:
    """Encapsulates statuses and info of a Condor cluster."""

    def __init__(self) -> None:
        self._jobs: dict[int, dict[str, Any]] = {}
        self._previous_aggregate_statuses: dict[str, dict[str, int]] = {}
        self._previous_aggregate_top_task_errors: dict[str, int] = {}

    def aggregate_statuses(
        self,
    ) -> dict[str, dict[str, int]]:
        """Aggregate statuses of jobs & return whether this is an new value."""

        def transform_job_status_val(info: dict[str, Any]) -> str:
            """Get job status -- transforming any as needed.

            NOTE: each transformation needs to be generic
            enough to aggregate nicely with others; e.g. don't
            append a timestamp, do append a standard reason str.
            """
            # FIXME
            if info["JobStatus"] == ct.HELD:
                codes = (
                    info.get("HoldReasonCode", None),
                    info.get("HoldReasonSubCode", None),
                )
                return (
                    f"{ct.job_status_to_str(ct.HELD)}: "
                    f"{codes} "
                    f"{info.get('HoldReason', 'unknown reason')}"
                )
            else:
                return ct.job_status_to_str(info["JobStatus"])

        statuses: dict[str, dict[str, int]] = {
            k: {}
            for k in set(transform_job_status_val(info) for info in self._jobs.values())
        }

        for job_status in statuses:
            ids_for_this_job_status = [  # subset of cluster_info ids
                i
                for i, info in self._jobs.items()
                if transform_job_status_val(info) == job_status
            ]
            # NOTE - if the pilot did not send a status (ex: Held job), it is `None`
            statuses[job_status] = dict(
                collections.Counter(
                    self._jobs[i]["HTChirpEWMSPilotStatus"]
                    for i in ids_for_this_job_status
                )
            )

        # validate & return
        if statuses == self._previous_aggregate_statuses:
            raise NoUpdateException()
        self._previous_aggregate_statuses = statuses
        return self._previous_aggregate_statuses

    def aggregate_top_task_errors(
        self,
    ) -> dict[str, int]:
        """Aggregate top X errors of jobs & return whether this is an new
        value."""
        counts = collections.Counter(
            dicto.get("HTChirpEWMSPilotError") for dicto in self._jobs.values()
        )
        counts.pop(None, None)  # remove counts of "no error"

        errors = dict(counts.most_common(WATCHER_N_TOP_TASK_ERRORS))

        # validate & return
        if errors == self._previous_aggregate_top_task_errors:
            raise NoUpdateException()
        self._previous_aggregate_top_task_errors = errors  # type: ignore[assignment]
        return self._previous_aggregate_top_task_errors

    def update_from_event(
        self,
        job_event: htcondor.JobEvent,
    ) -> None:
        """Extract the meaningful info from the event for the cluster."""
        #
        # CHIRP
        if job_event.type == htcondor.JobEvent.GENERIC:
            if not (info := job_event.get("info", None)):
                raise UnknownEvent()
            # ex: "HTChirpEWMSPilotStatus: foo bar baz"
            if not info.startswith("HTChirpEWMSPilot"):
                raise UnknownEvent()
            # parse
            attr, value = info.split(":", maxsplit=1)
            self._jobs[job_event.proc][attr] = value.strip()
        #
        # JOB STATUS
        elif job_status := ct.JOB_EVENT_STATUS_TRANSITIONS.get(job_event.type, None):
            self._jobs[job_event.proc]["HTChirpEWMSPilotStatus"] = job_status.__name__
        #
        # OTHER
        else:
            raise UnknownEvent()


class EveryXSeconds:
    """Keep track of durations."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self._last_time = time.time()

    def has_been_x_seconds(self) -> bool:
        """Has it been at least `self.seconds` since last time?"""
        yes = time.time() - self._last_time >= self.seconds
        if yes:
            self._last_time = time.time()
        return yes


async def watch_job_event_log(jel_fpath: Path) -> None:
    """Watch over one job event log file."""

    # make connections -- do now so we don't have any surprises downstream
    ewms_rc = RestClient(ENV.EWMS_ADDRESS, token=ENV.EWMS_AUTH)
    LOGGER.info("Connected to EWMS")

    all_clusters: dict[str, ClusterInfo] = {}  # LARGE

    time_tracker = EveryXSeconds(WATCHER_INTERVAL)

    jel = htcondor.JobEventLog(str(jel_fpath))
    jel_index = -1

    while True:
        # wait for job log to populate (more)
        while not time_tracker.has_been_x_seconds():
            await asyncio.sleep(1)

        # get events -- exit when no more events, or took too long
        for job_event in jel.events(stop_after=0):  # 0 -> only get currently available
            jel_index += 1
            taskforce_uuid = "foo"  # TODO -- map cluster id to tf-uuid
            if taskforce_uuid not in all_clusters:
                all_clusters[taskforce_uuid] = ClusterInfo()
            all_clusters[taskforce_uuid].update_from_event(job_event)
            if time_tracker.has_been_x_seconds():
                break
            await asyncio.sleep(0)  # since htcondor is not async

        # TODO -- idea: at this point there is redundant info in all_clusters,
        # can we clear up data by only keeping the aggregate info? maybe

        # aggregate
        top_task_errors = {}
        for cluster_id, info in all_clusters.items():
            try:
                top_task_errors[cluster_id] = info.aggregate_top_task_errors()
            except NoUpdateException:
                pass
        statuses = {}
        for cluster_id, info in all_clusters.items():
            try:
                statuses[cluster_id] = info.aggregate_statuses()
            except NoUpdateException:
                pass

        # send -- one big update that way it won't intermittently fail
        await ewms_rc.request(
            "PATCH",
            "/taskforce/many",
            {
                "jel_index": jel_index,
                "top_task_errors": top_task_errors,
                "statuses": statuses,
            },
        )

    # TODO -- delete file
