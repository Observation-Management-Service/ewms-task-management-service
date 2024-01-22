"""General Utilities."""


import logging
import time

from rest_tools.client import RestClient

LOGGER = logging.getLogger(__name__)


async def is_taskforce_to_be_aborted(ewms_rc: RestClient, taskforce_uuid: str) -> bool:
    """Return whether the taskforce has been signaled for removal."""
    ret = await ewms_rc.request(
        "GET",
        f"/tms/taskforce/{taskforce_uuid}",
    )
    return ret["is_deleted"]  # type: ignore[no-any-return]


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
