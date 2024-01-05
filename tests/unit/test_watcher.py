"""Unit tests for the watcher."""


import os
from pathlib import Path
from unittest import mock
from unittest.mock import Mock

from tms.watcher import watcher


@mock.patch("rest_tools.client.RestClient")
async def test_000(rc_mock: Mock) -> None:
    """Test the watcher."""
    fpath = Path(os.environ["JOB_EVENT_LOG_DIR"]) / "condor_test_logfile"

    await watcher.watch_job_event_log(fpath)

    assert 0  # TODO
