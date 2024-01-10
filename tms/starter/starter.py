"""For starting EWMS taskforce workers on an HTCondor cluster."""


import logging
from datetime import date
from pathlib import Path
from typing import Any, Awaitable

import htcondor  # type: ignore[import-untyped]
import humanfriendly

from ..config import ENV

LOGGER = logging.getLogger(__name__)


def make_condor_job_description(
    # taskforce args
    image: str,
    arguments: str,
    environment: dict[str, str],
    input_files: list[str],
    taskforce_uuid: str,
    # condor args
    do_transfer_worker_stdouterr: bool,
    max_worker_runtime: int,
    n_cores: int,
    priority: int,
    worker_disk_bytes: int,
    worker_memory_bytes: int,
) -> dict[str, Any]:
    """Make the condor job description (dict)."""

    # NOTE:
    # In the newest version of condor we could use:
    #   universe = container
    #   container_image = ...
    #   arguments = python -m ...
    # But for now, we're stuck with:
    #   executable = ...
    #   +SingularityImage = ...
    #   arguments = /usr/local/icetray/env-shell.sh python -m ...
    # Because "this universe doesn't know how to do the
    #   entrypoint, and loading the icetray env file
    #   directly from cvmfs messes up the paths" -DS

    environment_str = " ".join(f"{k}={v}" for k, v in environment.items())
    input_files_str = " ".join(input_files)

    # cluster logs -- shared w/ other clusters
    ENV.JOB_EVENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    logs_fpath = ENV.JOB_EVENT_LOG_DIR / f"tms-{date.today()}.log"  # tms-2024-1-27.log

    # write
    submit_dict = {
        "executable": "/bin/bash",
        "arguments": arguments,
        "+SingularityImage": f'"{image}"',  # must be quoted
        "Requirements": "HAS_CVMFS_icecube_opensciencegrid_org && has_avx && has_avx2",
        "environment": f'"{environment_str}"',  # must be quoted
        "+FileSystemDomain": '"blah"',  # must be quoted
        #
        "transfer_input_files": f'"{input_files_str}"',  # must be quoted
        #
        "log": str(logs_fpath),
        "transfer_output_files": str(logs_fpath),  # must be quoted for "none"
        # https://htcondor.readthedocs.io/en/latest/users-manual/file-transfer.html#specifying-if-and-when-to-transfer-files
        "should_transfer_files": "YES",
        "when_to_transfer_output": "ON_EXIT_OR_EVICT",
        #
        # Don't transfer executable (/bin/bash) in case of
        #   version (dependency) mismatch.
        #     Ex:
        #     "/lib/x86_64-linux-gnu/libc.so.6: version `GLIBC_2.36' not found"
        # Technically this is just needed for spooling -- since if
        #   we don't spool, the executable (/bin/bash) can't be
        #   transferred anyway and so a local version will be used
        "transfer_executable": "false",
        #
        "request_cpus": str(n_cores),
        "request_memory": humanfriendly.format_size(  # 1073741824 -> "1 GiB" -> "1 GB"
            worker_memory_bytes, binary=True
        ).replace("i", ""),
        "request_disk": humanfriendly.format_size(  # 1073741824 -> "1 GiB" -> "1 GB"
            worker_disk_bytes, binary=True
        ).replace("i", ""),
        "priority": int(priority),
        "+WantIOProxy": "true",  # for HTChirp
        "+OriginalTime": max_worker_runtime,  # Execution time limit -- 1 hour default on OSG
        #
        "+EWMSTaskforceUUID": f'"{taskforce_uuid}"',  # must be quoted
        "job_ad_information_attrs": "EWMSTaskforceUUID",
    }

    # worker stdout & stderr
    if do_transfer_worker_stdouterr:
        # this is the location where the files will go when/if *returned here*
        cluster_subdir = logs_fpath.parent / "tms-cluster-$(ClusterId)"
        submit_dict.update(
            {
                "output": str(cluster_subdir / "$(ProcId).out"),
                "error": str(cluster_subdir / "$(ProcId).err"),
            }
        )
        submit_dict.update(
            {
                "transfer_output_files": ",".join(
                    submit_dict["transfer_output_files"].split(",")
                    + [
                        submit_dict["output"],
                        submit_dict["error"],
                    ]
                ),
            }
        )

    LOGGER.info(submit_dict)
    return submit_dict


def submit(
    schedd_obj: htcondor.Schedd,
    n_workers: int,
    submit_dict: dict[str, Any],
) -> htcondor.SubmitResult:
    """Start taskforce on Condor cluster."""
    submit_obj = htcondor.Submit(submit_dict)
    LOGGER.info(submit_obj)

    # submit
    submit_result_obj = schedd_obj.submit(
        submit_obj,
        count=n_workers,  # submit N workers
    )
    LOGGER.info(submit_result_obj)

    return submit_result_obj


async def start(
    schedd_obj: htcondor.Schedd,
    is_aborted_awaitable: Awaitable[bool],
    #
    n_workers: int,
    # taskforce args
    image: str,
    arguments: str,
    environment: dict[str, str],
    input_files: list[str],
    taskforce_uuid: str,
    # condor args
    do_transfer_worker_stdouterr: bool,
    max_worker_runtime: int,
    n_cores: int,
    priority: int,
    worker_disk_bytes: int,
    worker_memory_bytes: int,
) -> dict[str, Any]:
    LOGGER.info(
        f"Starting {n_workers} EWMS taskforce workers on {ENV.COLLECTOR} / {ENV.SCHEDD}"
    )

    # prep
    submit_dict = make_condor_job_description(
        image,
        arguments,
        environment,
        input_files,
        taskforce_uuid,
        #
        do_transfer_worker_stdouterr,
        max_worker_runtime,
        n_cores,
        priority,
        worker_disk_bytes,
        worker_memory_bytes,
    )

    # final checks
    if ENV.DRYRUN:
        LOGGER.critical("Script Aborted: dryrun enabled")
        return {}
    if await is_aborted_awaitable:
        LOGGER.critical(f"Script Aborted: EWMS aborted taskforce: {taskforce_uuid}")
        return {}

    # submit
    submit_result_obj = submit(
        schedd_obj=schedd_obj,
        n_workers=n_workers,
        submit_dict=submit_dict,
    )

    # assemble attrs for EWMS
    ewms_taskforce_attrs = dict(
        orchestrator="condor",
        location={
            "collector": ENV.COLLECTOR,
            "schedd": ENV.SCHEDD,
        },
        taskforce_uuid=taskforce_uuid,
        cluster_id=submit_result_obj.cluster(),
        n_workers=submit_result_obj.num_procs(),
        starter_info=submit_dict,
    )
    return ewms_taskforce_attrs
