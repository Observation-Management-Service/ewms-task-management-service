"""Unit tests for the starter functionality."""


import logging
import os
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import htcondor  # type: ignore[import-untyped]
import humanfriendly
from tms import config  # noqa: F401  # setup env vars
from tms.scalar import starter

LOGGER = logging.getLogger(__name__)


htcondor.enable_debug()


@patch(
    "htcondor.param",
    new=dict(
        CONDOR_HOST=os.environ["_TEST_COLLECTOR"],
        FULL_HOSTNAME=os.environ["_TEST_SCHEDD"],
    ),
)
@patch("tms.scalar.starter.is_taskforce_still_pending_starter")
@patch("htcondor.Submit")
async def test_000(htcs_mock: MagicMock, itsps_mock: AsyncMock) -> None:
    """Test the starter."""
    schedd_obj = MagicMock()
    itsps_mock.return_value = True

    submit_dict = {
        "executable": "/bin/bash",
        "arguments": "my args",
        "+SingularityImage": '"my_image"',  # must be quoted
        "Requirements": "HAS_CVMFS_icecube_opensciencegrid_org && has_avx && has_avx2",
        "environment": '"EWMS_PILOT_HTCHIRP=True EWMS_PILOT_HTCHIRP_VIA_JOB_EVENT_LOG=True abc=932 def=True"',  # must be quoted
        "+FileSystemDomain": '"blah"',  # must be quoted
        #
        "transfer_input_files": '"foofile bardir/barfile"',  # must be quoted
        #
        "log": str(config.ENV.JOB_EVENT_LOG_DIR / f"tms-{date.today()}.log"),
        "should_transfer_files": "YES",
        "when_to_transfer_output": "ON_EXIT_OR_EVICT",
        #
        "transfer_executable": "false",
        #
        "request_cpus": str(64),
        "request_memory": humanfriendly.format_size(  # 1073741824 -> "1 GiB" -> "1 GB"
            4235, binary=True
        ).replace("i", ""),
        "request_disk": humanfriendly.format_size(  # 1073741824 -> "1 GiB" -> "1 GB"
            85461235, binary=True
        ).replace("i", ""),
        "priority": int(100),
        "+WantIOProxy": "true",  # for HTChirp
        "+OriginalTime": 95487,  # Execution time limit -- 1 hour default on OSG
        #
        "+EWMSTaskforceUUID": '"9874abcdef"',  # must be quoted
        "job_ad_information_attrs": "EWMSTaskforceUUID",
        #
        #
        "output": str(
            config.ENV.JOB_EVENT_LOG_DIR / "tms-cluster-$(ClusterId)" / "$(ProcId).out"
        ),
        "error": str(
            config.ENV.JOB_EVENT_LOG_DIR / "tms-cluster-$(ClusterId)" / "$(ProcId).err"
        ),
        "transfer_output_files": "",
    }

    ret = await starter.start(
        schedd_obj=schedd_obj,
        ewms_rc=MagicMock(),
        #
        n_workers=123,
        # taskforce args
        image="my_image",
        arguments="my args",
        environment={"abc": "932", "def": "True"},
        input_files=["foofile", "bardir/barfile"],
        taskforce_uuid="9874abcdef",
        # condor args
        do_transfer_worker_stdouterr=True,
        max_worker_runtime=95487,
        n_cores=64,
        priority=100,
        worker_disk=85461235,
        worker_memory=4235,
    )

    itsps_mock.assert_awaited_once()

    htcs_mock.assert_called_with(submit_dict)
    schedd_obj.submit.assert_called_with(
        htcs_mock.return_value,
        count=123,  # submit N workers
    )

    assert ret == dict(
        cluster_id=schedd_obj.submit.return_value.cluster.return_value,
        n_workers=schedd_obj.submit.return_value.num_procs.return_value,
        submit_dict=submit_dict,
        job_event_log_fpath=str(
            config.ENV.JOB_EVENT_LOG_DIR / f"tms-{date.today()}.log"
        ),
    )
