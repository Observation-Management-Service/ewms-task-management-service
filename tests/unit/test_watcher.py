"""Unit tests for the watcher."""


import asyncio
import os
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import htcondor
from tms import config  # noqa: F401  # setup env vars
from tms.watcher import watcher

LIVE_UPDATE_SLEEP = 2


async def mimick_live_file_updates(src: Path, live_file: Path, n_updates: int) -> None:
    with open(src) as f:  # thread safe b/c only reading
        lines = f.readlines()

    for i in range(n_updates):
        with open(live_file, "w") as livef:
            amount = ((i + 1) / n_updates) * len(lines)
            livef.write("".join(lines[: int(amount)]))
        with open(live_file) as livef:
            print(livef.read())  # TODO
        await asyncio.sleep(LIVE_UPDATE_SLEEP)


async def test_000() -> None:
    """Test the watcher."""
    htcondor.enable_debug()

    src = Path(os.environ["JOB_EVENT_LOG_DIR"]) / "condor_test_logfile"
    fpath = Path(src.name + "-live")

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
