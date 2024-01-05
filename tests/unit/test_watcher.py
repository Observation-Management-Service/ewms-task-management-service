"""Unit tests for the watcher."""


import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from tms import config  # noqa: F401  # setup env vars
from tms.watcher import watcher


async def test_000() -> None:
    """Test the watcher."""
    fpath = Path(os.environ["JOB_EVENT_LOG_DIR"]) / "condor_test_logfile"

    rc = MagicMock()
    rc.request = AsyncMock(side_effect={})
    await watcher.watch_job_event_log(fpath, rc)

    assert 0  # TODO
