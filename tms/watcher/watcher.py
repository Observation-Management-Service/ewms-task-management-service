"""For watching EWMS taskforce workers on an HTCondor cluster."""


import asyncio
import collections
import json
import logging
import pprint
from pathlib import Path
from typing import Any

import htcondor  # type: ignore[import-untyped]
from rest_tools.client import RestClient

from .. import condor_tools, types
from ..config import ENV, WATCHER_N_TOP_TASK_ERRORS
from ..utils import AppendOnlyList, EveryXSeconds, TaskforceMonitor
from .utils import (
    JobInfoKey,
    JobInfoVal,
    is_jel_okay_to_delete,
    job_info_val_to_string,
    query_for_more_taskforces,
    send_condor_complete,
)

_ALL_TOP_ERRORS_KEY = "top_task_errors_by_taskforce"
_ALL_COMP_STAT_KEY = "compound_statuses_by_taskforce"


LOGGER = logging.getLogger(__name__)


class UnknownJobEvent(Exception):
    """Raise when the job event is not valid for these purposes."""


class ReceivedClusterRemovedJobEvent(Exception):
    """Raise when a job event signally the cluster has been removed is seen."""

    def __init__(self, timestamp: int):
        self.timestamp = timestamp
        super().__init__()


class NoUpdateException(Exception):
    """Raise when there is no update to be made."""


########################################################################################


class ClusterInfo:
    """Encapsulates statuses and info of a Condor cluster."""

    def __init__(self, tmonitor: TaskforceMonitor) -> None:
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
        elif job_status := condor_tools.JOB_EVENT_STATUS_TRANSITIONS.get(
            job_event.type
        ):
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
        #
        elif job_event.type == htcondor.JobEventType.CLUSTER_REMOVE:
            raise ReceivedClusterRemovedJobEvent(int(job_event.timestamp))

        #
        # OTHER
        else:
            raise UnknownJobEvent(f"not an important event: {job_event.type.name}")


########################################################################################


async def watch_job_event_log(
    jel_fpath: Path,
    ewms_rc: RestClient,
    tmonitors: AppendOnlyList[TaskforceMonitor],
) -> None:
    """Watch over one JEL file, containing multiple taskforces.

    NOTE:
        1. a taskforce is never split among multiple files, it uses only one
        2. if this process crashes, the file will be re-read from the top;
            so, there's no need to track progress.
    """
    LOGGER.info(f"This watcher will read {jel_fpath}")

    cluster_infos: dict[types.ClusterId, ClusterInfo] = {}  # LARGE
    interval_timer = EveryXSeconds(ENV.TMS_WATCHER_INTERVAL)
    jel = htcondor.JobEventLog(str(jel_fpath))

    while True:
        # wait for JEL to populate (more)
        await interval_timer.wait_until_x(LOGGER)

        # query for new taskforces, so we wait for any
        #   taskforces/clusters that are late to start by condor
        #   (and are not yet in the JEL)
        async for taskforce_uuid, cluster_id in query_for_more_taskforces(
            ewms_rc,
            jel_fpath,
            list(c.taskforce_uuid for c in cluster_infos.values()),
        ):
            cluster_infos[cluster_id] = ClusterInfo(
                TaskforceMonitor(taskforce_uuid, cluster_id)
            )
            tmonitors.append(cluster_infos[cluster_id].tmonitor)

        # get events -- exit when no more events
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
                    f"Cluster found in JEL does not match any "
                    f"known taskforce ({job_event.cluster}), skipping it"
                )
                continue
            except ReceivedClusterRemovedJobEvent as e:
                await send_condor_complete(
                    ewms_rc,
                    cluster_infos[job_event.cluster].taskforce_uuid,
                    e.timestamp,
                )
            except UnknownJobEvent as e:
                LOGGER.debug(f"error: {e}")

        # endgame check
        if (not got_new_events) and all(c.seen_in_jel for c in cluster_infos.values()):
            if await is_jel_okay_to_delete(ewms_rc, jel_fpath):
                jel_fpath.unlink()  # delete file
                LOGGER.warning(f"Deleted JEL file {jel_fpath}")
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
        #  Alternatively, we could re-parse the entire JEL every time.
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
        # remove any "empty" keys
        # (it's okay to send an empty sub-dict, but all empties is pointless)
        if patch_body := {k: v for k, v in patch_body.items() if v}:
            LOGGER.info("SENDING UPDATES TO EWMS...")
            await ewms_rc.request(
                "POST",
                "/taskforces/tms/report",
                patch_body,
            )
            LOGGER.info("UPDATES SENT.")
        else:
            LOGGER.info("NO UPDATES NEEDED FOR EWMS")
