"""Unit tests."""


import os
from pathlib import Path

from tms import watcher


async def test_000__watcher() -> None:
    """Test the watcher."""
    fpath = Path(os.environ["CI_TEST_JOB_EVENT_LOG_FILE"])

    watcher.watcher.watch_job_event_log(fpath)  # type: ignore[attr-defined]

    assert 0  # TODO
