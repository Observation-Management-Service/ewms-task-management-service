"""Unit tests for the watcher."""


import asyncio
import os
import threading
from pathlib import Path
from typing import Iterator
from unittest.mock import AsyncMock, MagicMock

import htcondor  # type: ignore[import-untyped]
import pytest
from tms import config  # noqa: F401  # setup env vars
from tms.watcher import watcher

LIVE_UPDATE_SLEEP = 2

htcondor.enable_debug()


class JobEventLogFileWrapper:
    """explain."""

    def __init__(self, src: Path) -> None:
        self.src = src
        self.live_file = Path(src.name + "-live")
        self.live_file.touch()  # watcher assumes file exists

    @staticmethod
    def _get_subset_job_event_log(lines: list[str], min_amount: int) -> Iterator[str]:
        """Get a subset of the job event log and maintain valid syntax."""
        for i, ln in enumerate(lines):
            yield ln
            if i >= min_amount and ln == "...\n":
                return

    def start_live_file_updates(self, n_updates: int) -> None:
        """Begin updating live file by iteratively adding lines from src."""
        threading.Thread(
            target=asyncio.run,
            args=(self._mimick_live_file_updates(n_updates),),
            daemon=True,
        ).start()

    async def _mimick_live_file_updates(self, n_updates: int) -> None:
        with open(self.src) as f:  # thread safe b/c only reading
            lines = f.readlines()

        for i in range(n_updates):
            await asyncio.sleep(LIVE_UPDATE_SLEEP)
            with open(self.live_file, "w") as livef:
                amount = ((i + 1) / n_updates) * len(lines)
                subset_lines = self._get_subset_job_event_log(lines, int(amount))
                livef.write("".join(subset_lines))
            # with open(live_file) as livef:
            #     print(livef.read())

        # now add an "unimportant" event (no ewms update needed)
        await asyncio.sleep(LIVE_UPDATE_SLEEP)
        with open(self.live_file, "w") as livef:
            more_lines = lines[:]  # copy
            more_lines.extend(
                [
                    "008 (104501503.002.000) 2024-01-05 12:29:24 Goodbye from job 3\n",
                    "...\n",
                ]
            )
            livef.write("".join(more_lines))


@pytest.fixture
def jel_file_wrapper() -> JobEventLogFileWrapper:
    """Job event log file."""
    src = Path(os.environ["JOB_EVENT_LOG_DIR"]) / "condor_test_logfile"
    return JobEventLogFileWrapper(src)


async def test_000(jel_file_wrapper: JobEventLogFileWrapper) -> None:
    """Test the watcher."""
    n_updates = 5

    # update file in background
    jel_file_wrapper.start_live_file_updates(n_updates)

    rc = MagicMock()
    rc.request = AsyncMock(return_value={})
    await watcher.watch_job_event_log(jel_file_wrapper.live_file, rc)

    assert rc.request.call_count == n_updates
    assert rc.request.call_args_list == [
        ("PATCH", "/tms/condor-cluster/many", {}),
        ("PATCH", "/tms/condor-cluster/many", {}),
        ("PATCH", "/tms/condor-cluster/many", {}),
        ("PATCH", "/tms/condor-cluster/many", {}),
        ("PATCH", "/tms/condor-cluster/many", {}),
    ]

    assert 0  # TODO
