"""General Utilities."""


import logging
import time
from typing import TypeVar

from rest_tools.client import RestClient

from . import types

LOGGER = logging.getLogger(__name__)


async def is_taskforce_still_pending_start(
    ewms_rc: RestClient,
    taskforce_uuid: str,
) -> bool:
    """Return whether the taskforce is still pending-start."""
    ret = await ewms_rc.request(
        "GET",
        f"/tms/taskforce/{taskforce_uuid}",
    )
    return ret["tms_status"] == "pending-start"  # type: ignore[no-any-return]


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
