"""General Utilities."""

import logging
from datetime import date
from pathlib import Path
from typing import TypeVar

from rest_tools.client import ClientCredentialsAuth, RestClient

from . import types
from .condor_tools import get_collector, get_schedd
from .config import ENV, WMS_URL_V_PREFIX

LOGGER = logging.getLogger(__name__)


def connect_to_ewms() -> RestClient:
    """Connect to EWMS API."""
    LOGGER.info("Connecting to EWMS...")
    return ClientCredentialsAuth(
        ENV.EWMS_ADDRESS,
        ENV.EWMS_TOKEN_URL,
        ENV.EWMS_CLIENT_ID,
        ENV.EWMS_CLIENT_SECRET,
    )


class LogFileLogic:
    """Logic for setting up and detecting log files."""

    @staticmethod
    def make_log_file_name() -> Path:
        """Generate a log file name."""
        ENV.JOB_EVENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
        return ENV.JOB_EVENT_LOG_DIR / f"tms-{date.today()}.log"  # tms-2024-1-27.log

    @staticmethod
    def is_log_file(fpath: Path) -> bool:
        """Return whether the log file exists and has a valid log filename."""
        return bool(
            fpath.is_file() and fpath.name.startswith("tms-") and fpath.suffix == ".log"
        )


class TaskforceMonitor:
    """For storing minimal data on a taskforce through its lifetime."""

    def __init__(self, taskforce_uuid: str, cluster_id: types.ClusterId) -> None:
        self.taskforce_uuid = taskforce_uuid
        self.cluster_id = cluster_id

        self.aggregate_statuses: types.AggregateStatuses = {}
        self.top_task_errors: types.TopTaskErrors = {}


T = TypeVar("T")


class AppendOnlyList(list[T]):
    """A list you cannot explicitly remove items from."""

    def remove(self, *args):
        raise NotImplementedError()

    def pop(self, *args):
        raise NotImplementedError()

    def clear(self, *args):
        raise NotImplementedError()


async def is_jel_no_longer_used(jel_fpath: Path) -> bool:
    """Return whether there are no non-completed taskforces using JEL."""
    ewms_rc = connect_to_ewms()

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
        LOGGER.warning("There are no non-completed taskforces using JEL -- CAN DELETE")
    return not is_used
