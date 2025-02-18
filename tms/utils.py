"""General Utilities."""

import logging
from datetime import date
from pathlib import Path
from typing import TypeVar

from . import types
from .config import ENV

LOGGER = logging.getLogger(__name__)


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
