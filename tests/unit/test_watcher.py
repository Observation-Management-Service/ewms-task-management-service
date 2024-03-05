"""Unit tests for the watcher."""


import asyncio
import logging
import os
import threading
from pathlib import Path
from typing import Iterator
from unittest.mock import AsyncMock, MagicMock, call, patch

import htcondor  # type: ignore[import-untyped]
import pytest
from tms import config  # noqa: F401  # import in order to set up env vars
from tms import utils
from tms.watcher import watcher

LOGGER = logging.getLogger(__name__)


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
        """Get a subset of the JEL and maintain valid syntax."""
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
                    "008 (123.002.000) 2024-01-05 12:29:24 Goodbye from job 3\n",
                    "...\n",
                ]
            )
            livef.write("".join(more_lines))


@pytest.fixture
def jel_file_wrapper() -> JobEventLogFileWrapper:
    """JEL file."""
    src = Path(os.environ["JOB_EVENT_LOG_DIR"]) / "condor_test_logfile"
    return JobEventLogFileWrapper(src)


########################################################################################


@patch("tms.condor_tools.get_collector", new=lambda: os.environ["_TEST_COLLECTOR"])
@patch("tms.condor_tools.get_schedd", new=lambda: os.environ["_TEST_SCHEDD"])
async def test_000(jel_file_wrapper: JobEventLogFileWrapper) -> None:
    """Test the watcher."""
    n_updates = 5

    # update file in background
    jel_file_wrapper.start_live_file_updates(n_updates)

    def mock_all_requests(*args, **kwargs):
        # fmt: off
        if args[:2] == ("POST", "/taskforces/find") and args[2]["query"].get("condor_complete_ts") == {"$ne": None}:
            # this call only happens after the JEL is expired, so for these tests, ignoring it is fine
            return {"taskforces": []}
        # fmt: on
        elif args[:2] == ("POST", "/taskforces/find"):
            return {
                "taskforces": [
                    {"taskforce_uuid": "abc123", "cluster_id": 104501503},
                    {"taskforce_uuid": "def456", "cluster_id": 104500588},
                ]
            }
        elif args[:2] == ("POST", "/taskforces/tms/report"):
            return {}
        else:
            return Exception(f"unexpected request arguments: {args=}, {kwargs=}")

    tmonitors: utils.AppendOnlyList[utils.TaskforceMonitor] = utils.AppendOnlyList()
    rc = MagicMock()
    rc.request = AsyncMock(side_effect=mock_all_requests)
    await watcher.watch_job_event_log(jel_file_wrapper.live_file, rc, tmonitors)

    assert len(tmonitors) == 2  # check that the taskforce monitors is still here

    # assert POST calls
    post_calls = [
        c
        for c in rc.request.call_args_list
        if c.args[:2] == ("POST", "/taskforces/tms/report")
    ]
    assert len(post_calls) == n_updates
    assert post_calls == [
        call(
            "POST",
            "/taskforces/tms/report",
            {
                "top_task_errors_by_taskforce": {},
                "compound_statuses_by_taskforce": {
                    "abc123": {
                        "IDLE": {None: 5},
                        "REMOVED": {None: 1},
                        "COMPLETED": {"Done": 1},
                    },
                    "def456": {"REMOVED": {None: 1}},
                },
            },
        ),
        call(
            "POST",
            "/taskforces/tms/report",
            {
                "top_task_errors_by_taskforce": {},
                "compound_statuses_by_taskforce": {
                    "abc123": {
                        "IDLE": {None: 3},
                        "RUNNING": {None: 1},
                        "REMOVED": {None: 1},
                        "COMPLETED": {"Done": 2},
                    }
                },
            },
        ),
        call(
            "POST",
            "/taskforces/tms/report",
            {
                "top_task_errors_by_taskforce": {},
                "compound_statuses_by_taskforce": {
                    "abc123": {
                        "RUNNING": {None: 3},
                        "REMOVED": {None: 1},
                        "COMPLETED": {"Done": 3},
                    }
                },
            },
        ),
        call(
            "POST",
            "/taskforces/tms/report",
            {
                "top_task_errors_by_taskforce": {},
                "compound_statuses_by_taskforce": {
                    "abc123": {
                        "HELD: Memory usage exceeds a memory limit": {"Tasking": 1},
                        "RUNNING": {"Tasking": 1},
                        "REMOVED": {None: 1},
                        "COMPLETED": {"Done": 4},
                    }
                },
            },
        ),
        call(
            "POST",
            "/taskforces/tms/report",
            {
                "top_task_errors_by_taskforce": {},
                "compound_statuses_by_taskforce": {
                    "abc123": {
                        "HELD: Memory usage exceeds a memory limit": {"Tasking": 1},
                        "REMOVED": {None: 1},
                        "COMPLETED": {"Done": 5},
                    }
                },
            },
        ),
    ]

    # check that aggregates are not lost
    # - has last (non-null novel) value that was sent to EWMS
    tmonitor = next(t for t in tmonitors if t.taskforce_uuid == "abc123")
    assert tmonitor.cluster_id == 104501503
    assert tmonitor.top_task_errors == {}
    assert tmonitor.aggregate_statuses == {
        "HELD: Memory usage exceeds a memory limit": {"Tasking": 1},
        "REMOVED": {None: 1},
        "COMPLETED": {"Done": 5},
    }
    # - has last (non-null novel) value that was sent to EWMS
    tmonitor = next(t for t in tmonitors if t.taskforce_uuid == "def456")
    assert tmonitor.cluster_id == 104500588
    assert tmonitor.top_task_errors == {}
    assert tmonitor.aggregate_statuses == {"REMOVED": {None: 1}}
