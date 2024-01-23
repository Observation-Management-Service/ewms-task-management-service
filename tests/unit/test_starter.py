"""Unit tests for the starter functionality."""


from datetime import date
from unittest.mock import AsyncMock, MagicMock

import htcondor  # type: ignore[import-untyped]
import humanfriendly
from tms import config  # noqa: F401  # setup env vars
from tms.scalar import starter

htcondor.enable_debug()


async def test_000() -> None:
    """Test the starter."""
    is_aborted_awaitable = AsyncMock(return_value=False)
    schedd_obj = MagicMock()

    submit_dict = {
        "executable": "/bin/bash",
        "arguments": "my args",
        "+SingularityImage": '"my_image"',  # must be quoted
        "Requirements": "HAS_CVMFS_icecube_opensciencegrid_org && has_avx && has_avx2",
        "environment": '"abc=932 def=True"',  # must be quoted
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
        "transfer_output_files": (
            f'"{str(config.ENV.JOB_EVENT_LOG_DIR / f"tms-{date.today()}.log")},'
            f'{str(config.ENV.JOB_EVENT_LOG_DIR / "tms-cluster-$(ClusterId)" / "$(ProcId).out")},'
            f'{str(config.ENV.JOB_EVENT_LOG_DIR / "tms-cluster-$(ClusterId)" / "$(ProcId).err")}"'
        ),  # must be quoted
    }

    ret = await starter.start(
        schedd_obj=schedd_obj,
        is_aborted_awaitable=is_aborted_awaitable(),
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
        worker_disk_bytes=85461235,
        worker_memory_bytes=4235,
    )

    is_aborted_awaitable.assert_awaited_once()
    schedd_obj.submit.assert_called_with(
        htcondor.Submit(submit_dict),
        count=123,  # submit N workers
    )

    assert ret == dict(
        orchestrator="condor",
        location={
            "collector": config.ENV.COLLECTOR,
            "schedd": config.ENV.SCHEDD,
        },
        taskforce_uuid="9874abcdef",
        cluster_id="idk",
        n_workers=123,
        starter_info=submit_dict,
        job_event_log_fpath=str(
            config.ENV.JOB_EVENT_LOG_DIR / f"tms-{date.today()}.log"
        ),
    )
