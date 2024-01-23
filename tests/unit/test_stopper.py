"""Unit tests for the stopper functionality."""


from unittest.mock import MagicMock

import htcondor  # type: ignore[import-untyped]
from tms import config  # noqa: F401  # setup env vars
from tms.scalar import stopper

htcondor.enable_debug()


async def test_000() -> None:
    """Test the stopper."""
    schedd_obj = MagicMock()

    stopper.stop(schedd_obj, 123)

    schedd_obj.act.assert_called_with(
        htcondor.JobAction.Remove,
        f"ClusterId == {123}",
        reason="Requested by EWMS",
    )
