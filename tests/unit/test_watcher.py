"""Unit tests for the watcher."""


import os
from pathlib import Path

from tms.watcher import watcher


async def test_000() -> None:
    """Test the watcher."""
    fpath = Path(os.environ["JOB_EVENT_LOG_DIR"]) / "condor_test_logfile"

    await watcher.watch_job_event_log(fpath)

    assert 0  # TODO
