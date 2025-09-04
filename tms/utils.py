"""General Utilities."""

import logging
from datetime import date
from pathlib import Path
from typing import TypeVar

from rest_tools.client import RestClient

from . import types
from .condor_tools import get_collector, get_schedd
from .config import ENV, WMS_URL_V_PREFIX

LOGGER = logging.getLogger(__name__)


class JELFileLogic:
    """Logic for setting up and detecting job event log files."""

    parent = ENV.JOB_EVENT_LOG_DIR
    suffix = ".tms.jel"

    @staticmethod
    def create_path() -> Path:
        """Generate a log file name and mkdir parents."""
        JELFileLogic.parent.mkdir(parents=True, exist_ok=True)
        # ex: .../tms-2024-1-27.log
        return JELFileLogic.parent / f"{date.today()}{JELFileLogic.suffix}"

    @staticmethod
    def is_valid(fpath: Path) -> bool:
        """Return whether the log file exists and has a valid log filename."""
        return bool(
            fpath.parent == JELFileLogic.parent
            and fpath.is_file()
            and fpath.suffix == JELFileLogic.suffix
        )

    @staticmethod
    async def is_no_longer_used(ewms_rc: RestClient, fpath: Path) -> bool:
        """Return whether there are no non-completed taskforces using JEL."""
        resp = await ewms_rc.request(
            "POST",
            f"/{WMS_URL_V_PREFIX}/query/taskforces",
            {
                "query": {
                    "job_event_log_fpath": str(fpath),
                    "collector": get_collector(),
                    "schedd": get_schedd(),
                    "phase": {"$ne": "condor-complete"},  # only non-completed tfs
                },
                "projection": ["taskforce_uuid"],
            },
        )
        noncompleted_tfs = resp["taskforces"]

        if noncompleted_tfs:
            LOGGER.debug(
                f"There are still non-completed taskforces using JEL {fpath} -- DON'T DELETE"
            )
            return False  # no -- this file *IS* still used
        else:
            LOGGER.warning(
                f"There are no non-completed taskforces using JEL {fpath} -- POTENTIALLY DELETE"
            )
            return True  # yes -- this file is *NOT* being used


class TaskforceDirLogic:
    """Logic for setting up a taskforce dir."""

    parent = ENV.JOB_EVENT_LOG_DIR
    prefix = "ewms-taskforce-"

    @staticmethod
    def create(taskforce_uuid: str) -> Path:
        """Assemble and mkdir the taskforce's directory on the AP."""
        path = TaskforceDirLogic.parent / f"{TaskforceDirLogic.prefix}{taskforce_uuid}"
        path.mkdir(exist_ok=True)
        return path


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
