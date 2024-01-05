"""Unit tests."""


import os
from pathlib import Path

import tms


async def test_000__watcher() -> None:
    """Test the watcher."""
    fpath = Path(os.environ["CI_TEST_JOB_EVENT_LOG_FILE"])

    tms.watcher.watch_job_event_log(fpath)

    assert 0  # TODO
