"""Unit tests for the watcher."""


import os
from pathlib import Path

from tms.watcher import watcher


async def test_000() -> None:
    """Test the watcher."""
    fpath = Path(os.environ["CI_TEST_JOB_EVENT_LOG_FILE"])

    await watcher.watch_job_event_log(fpath)

    assert 0  # TODO
