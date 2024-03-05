"""Unit tests for the stopper functionality."""


import logging
import os
from unittest.mock import MagicMock, patch

import htcondor  # type: ignore[import-untyped]
from tms import config  # noqa: F401  # setup env vars
from tms.scalar import stopper

LOGGER = logging.getLogger(__name__)


htcondor.enable_debug()


@patch(
    "htcondor.param",
    new=dict(
        CONDOR_HOST=os.environ["_TEST_COLLECTOR"],
        FULL_HOSTNAME=os.environ["_TEST_SCHEDD"],
    ),
)
async def test_000() -> None:
    """Test the stopper."""
    schedd_obj = MagicMock()

    stopper.stop(schedd_obj, 123)

    schedd_obj.act.assert_called_with(
        htcondor.JobAction.Remove,
        f"ClusterId == {123}",
        reason="Requested by EWMS",
    )
