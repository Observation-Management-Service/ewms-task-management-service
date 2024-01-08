"""Unit tests for the watcher."""


import asyncio
import os
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from tms import config  # noqa: F401  # setup env vars
from tms.watcher import watcher

LIVE_UPDATE_SLEEP = 2


async def mimick_live_file_updates(src: Path, live_file: Path, n_updates: int) -> None:
    src_copy = Path("abc")
    shutil.copy(src, src_copy)

    with open(src_copy) as f:
        lines = f.readlines()

    for i in range(n_updates):
        await asyncio.sleep(LIVE_UPDATE_SLEEP)
        with open(live_file, "w") as livef:
            amount = ((i + 1) / n_updates) * len(lines)
            livef.write("".join(lines[: int(amount)]))


async def test_000() -> None:
    """Test the watcher."""
    src = Path(os.environ["JOB_EVENT_LOG_DIR"]) / "condor_test_logfile"
    fpath = Path(src.name + "-live")

    # update file in background task
    asyncio.create_task(mimick_live_file_updates(src, fpath, 5))

    rc = MagicMock()
    rc.request = AsyncMock(return_value={})
    await watcher.watch_job_event_log(fpath, rc)

    assert 0  # TODO
