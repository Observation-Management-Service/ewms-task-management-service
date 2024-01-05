"""Unit tests for the watcher."""


import os
from pathlib import Path
from unittest import mock
from unittest.mock import Mock

from tms.watcher import watcher


@mock.patch("tms.watcher.watcher.RestClient", new=Mock())
async def test_000() -> None:
    """Test the watcher."""
    fpath = Path(os.environ["JOB_EVENT_LOG_DIR"]) / "condor_test_logfile"

    await watcher.watch_job_event_log(fpath)

    assert 0  # TODO
