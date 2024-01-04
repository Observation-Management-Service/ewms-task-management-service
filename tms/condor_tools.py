"""Util functions wrapping common htcondor actions."""


import logging

import htcondor  # type: ignore[import-untyped]

LOGGER = logging.getLogger(__name__)


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
