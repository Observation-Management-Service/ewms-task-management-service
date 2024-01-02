"""Util functions wrapping common htcondor actions."""


import logging

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
