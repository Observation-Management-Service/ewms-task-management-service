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

from tms import config, utils  # noqa: F401  # import in order to set up env vars
from tms.watcher import watcher

htcondor.enable_debug()

LOGGER = logging.getLogger(__name__)

LIVE_UPDATE_SLEEP = 2

_WMS_PREFIX = "v1"


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


@patch(
    "htcondor.param",
    new=dict(
        CONDOR_HOST=os.environ["_TEST_COLLECTOR"],
        FULL_HOSTNAME=os.environ["_TEST_SCHEDD"],
    ),
)
async def test_000(jel_file_wrapper: JobEventLogFileWrapper) -> None:
    """Test the watcher."""
    n_updates = 5

    # update file in background
    jel_file_wrapper.start_live_file_updates(n_updates)

    def mock_all_requests(*args, **kwargs):
        if args[:2] == ("POST", f"/{_WMS_PREFIX}/query/taskforces"):
            # AKA - "is JEL expired?" check
            if args[2]["query"].get("condor_complete_ts") == {"$ne": None}:
                # this call only happens after the JEL is expired, so for these tests, ignoring it is fine
                return {"taskforces": []}
            # AKA - get all the taskforces
            elif list(args[2]["query"].keys()) == [
                "collector",
                "schedd",
                "job_event_log_fpath",
            ]:
                return {
                    "taskforces": [
                        {"taskforce_uuid": "abc123", "cluster_id": 104501503},
                        {"taskforce_uuid": "def456", "cluster_id": 104500588},
                    ]
                }
            # AKA - match cluster to taskforce
            elif list(args[2]["query"].keys()) == [
                "collector",
                "schedd",
                "job_event_log_fpath",
                "cluster_id",
            ]:
                return {"taskforces": [{"taskforce_uuid": "ghi789"}]}
            # ???
            else:
                raise RuntimeError(f"missing ewms patch: {args=}")
        elif args[:2] == ("POST", f"/{_WMS_PREFIX}/tms/statuses/taskforces"):
            return {}
        else:
            return Exception(f"unexpected request arguments: {args=}, {kwargs=}")

    rc = MagicMock()
    rc.request = AsyncMock(side_effect=mock_all_requests)
    jel_watcher = watcher.JobEventLogWatcher(jel_file_wrapper.live_file, rc)
    with pytest.raises(asyncio.TimeoutError):
        # use timeout otherwise this would run forever
        await asyncio.wait_for(
            jel_watcher.start(),
            timeout=int(os.environ["TMS_WATCHER_INTERVAL"]) * n_updates * 3,  # cushion
        )

    assert len(jel_watcher.cluster_infos) == 3  # check that collection is still here
    assert sorted(
        (x.taskforce_uuid, x.cluster_id) for x in jel_watcher.cluster_infos.values()
    ) == sorted(
        [
            # from initial ingestion (ewms)
            ("abc123", 104501503),
            ("def456", 104500588),
            # from JEL (cluster id from ewms)
            ("ghi789", 123),
        ]
    )

    # assert POST calls
    post_calls = [
        c
        for c in rc.request.call_args_list
        if c.args[:2] == ("POST", f"/{_WMS_PREFIX}/tms/statuses/taskforces")
    ]
    assert len(post_calls) == n_updates
    assert post_calls == [
        call(
            "POST",
            f"/{_WMS_PREFIX}/tms/statuses/taskforces",
            {
                # "top_task_errors_by_taskforce": {},
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
            f"/{_WMS_PREFIX}/tms/statuses/taskforces",
            {
                # "top_task_errors_by_taskforce": {},
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
            f"/{_WMS_PREFIX}/tms/statuses/taskforces",
            {
                # "top_task_errors_by_taskforce": {},
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
            f"/{_WMS_PREFIX}/tms/statuses/taskforces",
            {
                # "top_task_errors_by_taskforce": {},
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
            f"/{_WMS_PREFIX}/tms/statuses/taskforces",
            {
                # "top_task_errors_by_taskforce": {},
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
    cluster_info = next(
        v for v in jel_watcher.cluster_infos.values() if v.taskforce_uuid == "abc123"
    )
    assert cluster_info.cluster_id == 104501503
    assert cluster_info.top_task_errors == {}
    assert cluster_info.aggregate_statuses == {
        "HELD: Memory usage exceeds a memory limit": {"Tasking": 1},
        "REMOVED": {None: 1},
        "COMPLETED": {"Done": 5},
    }
    # - has last (non-null novel) value that was sent to EWMS
    cluster_info = next(
        v for v in jel_watcher.cluster_infos.values() if v.taskforce_uuid == "def456"
    )
    assert cluster_info.cluster_id == 104500588
    assert cluster_info.top_task_errors == {}
    assert cluster_info.aggregate_statuses == {"REMOVED": {None: 1}}
