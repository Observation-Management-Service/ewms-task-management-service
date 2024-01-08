"""Unit tests for the watcher."""


import asyncio
import os
import threading
from pathlib import Path
from typing import Iterator
from unittest.mock import AsyncMock, MagicMock

import htcondor  # type: ignore[import-untyped]
from tms import config  # noqa: F401  # setup env vars
from tms.watcher import watcher

LIVE_UPDATE_SLEEP = 2


def _get_subset_job_event_log(lines: list[str], min_amount: int) -> Iterator[str]:
    """Get a subset of the job event log and maintain valid syntax."""
    for i, ln in enumerate(lines):
        yield ln
        if i >= min_amount and ln == "...\n":
            return


async def mimick_live_file_updates(src: Path, live_file: Path, n_updates: int) -> None:
    """Routinely update the live file by iteratively adding lines from src."""
    with open(src) as f:  # thread safe b/c only reading
        lines = f.readlines()

    for i in range(n_updates):
        await asyncio.sleep(LIVE_UPDATE_SLEEP)
        with open(live_file, "w") as livef:
            amount = ((i + 1) / n_updates) * len(lines)
            subset_lines = _get_subset_job_event_log(lines, int(amount))
            livef.write("".join(subset_lines))
        # with open(live_file) as livef:
        #     print(livef.read())


async def test_000() -> None:
    """Test the watcher."""
    htcondor.enable_debug()

    # TODO - move to fixture
    src = Path(os.environ["JOB_EVENT_LOG_DIR"]) / "condor_test_logfile"
    fpath = Path(src.name + "-live")
    fpath.touch()  # watcher assumes file exists

    # update file in background
    threading.Thread(
        target=asyncio.run,
        args=(mimick_live_file_updates(src, fpath, 5),),
        daemon=True,
    ).start()

    rc = MagicMock()
    rc.request = AsyncMock(return_value={})
    await watcher.watch_job_event_log(fpath, rc)

    assert 0  # TODO
