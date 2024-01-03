"""Util functions wrapping common htcondor actions."""


import logging

import htcondor  # type: ignore[import-untyped]

LOGGER = logging.getLogger(__name__)


IDLE = 1
RUNNING = 2
REMOVED = 3
COMPLETED = 4
HELD = 5
TRANSFERRING_OUTPUT = 6
SUSPENDED = 7

_STATUS_MAPPING = {
    IDLE: "Idle",
    RUNNING: "Running",
    REMOVED: "Removed",
    COMPLETED: "Completed",
    HELD: "Held",
    TRANSFERRING_OUTPUT: "Transferring Output",
    SUSPENDED: "Suspended",
}


def job_status_to_str(status_code: int) -> str:
    """Get the human-readable string for the job status int."""
    return _STATUS_MAPPING.get(status_code, f"Invalid status code: {status_code}")


# from https://github.com/htcondor/htcondor/blob/main/src/condor_scripts/condor_watch_q#L1179
JOB_EVENT_STATUS_TRANSITIONS = {
    htcondor.JobEventType.SUBMIT: htcondor.JobStatus.IDLE,
    htcondor.JobEventType.JOB_EVICTED: htcondor.JobStatus.IDLE,
    htcondor.JobEventType.JOB_UNSUSPENDED: htcondor.JobStatus.IDLE,
    htcondor.JobEventType.JOB_RELEASED: htcondor.JobStatus.IDLE,
    htcondor.JobEventType.SHADOW_EXCEPTION: htcondor.JobStatus.IDLE,
    htcondor.JobEventType.JOB_RECONNECT_FAILED: htcondor.JobStatus.IDLE,
    htcondor.JobEventType.JOB_TERMINATED: htcondor.JobStatus.COMPLETED,
    htcondor.JobEventType.EXECUTE: htcondor.JobStatus.RUNNING,
    htcondor.JobEventType.JOB_HELD: htcondor.JobStatus.HELD,
    htcondor.JobEventType.JOB_SUSPENDED: htcondor.JobStatus.SUSPENDED,
    htcondor.JobEventType.JOB_ABORTED: htcondor.JobStatus.REMOVED,
}
