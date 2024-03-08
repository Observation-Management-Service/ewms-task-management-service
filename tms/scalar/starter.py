"""For starting EWMS taskforce workers on an HTCondor cluster."""


import logging
from datetime import date
from typing import Any

import htcondor  # type: ignore[import-untyped]
import humanfriendly
from rest_tools.client import RestClient

from ..condor_tools import get_collector, get_schedd
from ..config import ENV

LOGGER = logging.getLogger(__name__)


class HaltedByDryRun(Exception):
    """Raise when doing a dry run and no further progress is needed."""


class TaskforceNoLongerPendingStarter(Exception):
    """Raise when taskforce is not pending-starter when it is expected to
    be."""


async def is_taskforce_still_pending_starter(
    ewms_rc: RestClient,
    taskforce_uuid: str,
) -> bool:
    """Return whether the taskforce is still pending-starter."""
    ret = await ewms_rc.request(
        "GET",
        f"/taskforce/{taskforce_uuid}",
    )
    return ret["tms_most_recent_action"] == "pending-starter"  # type: ignore[no-any-return]


def make_condor_job_description(
    taskforce_uuid: str,
    # container_config
    image: str,
    arguments: str,
    environment: dict[str, str],
    input_files: list[str],
    # worker_config
    do_transfer_worker_stdouterr: bool,
    max_worker_runtime: int,
    n_cores: int,
    priority: int,
    worker_disk: int | str,
    worker_memory: int | str,
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

    # cluster logs -- shared w/ other clusters
    ENV.JOB_EVENT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    logs_fpath = ENV.JOB_EVENT_LOG_DIR / f"tms-{date.today()}.log"  # tms-2024-1-27.log

    # update environment
    environment.update(
        {
            "EWMS_PILOT_HTCHIRP": "True",
            "EWMS_PILOT_HTCHIRP_VIA_JOB_EVENT_LOG": "True",
        }
    )

    # write
    submit_dict = {
        "executable": "/bin/bash",
        "arguments": arguments.replace('"', r"\""),  # escape embedded quotes
        "+SingularityImage": f'"{image}"',  # must be quoted
        "Requirements": "HAS_CVMFS_icecube_opensciencegrid_org && has_avx && has_avx2",
        "environment": f'"{" ".join(f"{k}={v}" for k, v in environment.items())}"',  # must be quoted
        "+FileSystemDomain": '"blah"',  # must be quoted
        #
        "transfer_input_files": f'"{" ".join(input_files)}"',  # must be quoted
        #
        "log": str(logs_fpath),
        #
        "transfer_output_files": "",  # TODO: add ewms-pilot debug directory
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
        # NOTE: condor uses binary sizes but formats like decimal
        "request_memory": humanfriendly.format_size(
            # "1073741824" -> 1073741824 -> "1 GiB" -> "1 GB" (or "3 MB" -> 3221225472 -> "3 MB")
            humanfriendly.parse_size(str(worker_memory), binary=True),
            binary=True,
        ).replace("i", ""),
        # NOTE: condor uses binary sizes but formats like decimal
        "request_disk": humanfriendly.format_size(
            # "1073741824" -> 1073741824 -> "1 GiB" -> "1 GB" (or "3 MB" -> 3221225472 -> "3 MB")
            humanfriendly.parse_size(str(worker_disk), binary=True),
            binary=True,
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
    ewms_rc: RestClient,
    #
    taskforce_uuid: str,
    n_workers: int,
    # container_config
    image: str,
    arguments: str,
    environment: dict[str, str],
    input_files: list[str],
    # worker_config
    do_transfer_worker_stdouterr: bool,
    max_worker_runtime: int,
    n_cores: int,
    priority: int,
    worker_disk: int | str,
    worker_memory: int | str,
) -> dict[str, Any]:
    """Start an EWMS taskforce workers on an HTCondor cluster.

    Returns attrs for sending to EWMS.
    """
    LOGGER.info(
        f"Starting {n_workers} EWMS taskforce workers on {get_collector()} / {get_schedd()}"
    )

    # prep
    submit_dict = make_condor_job_description(
        taskforce_uuid,
        #
        image,
        arguments,
        environment,
        input_files,
        #
        do_transfer_worker_stdouterr,
        max_worker_runtime,
        n_cores,
        priority,
        worker_disk,
        worker_memory,
    )

    # final checks
    if ENV.DRYRUN:
        LOGGER.critical("Startup Aborted - dryrun enabled")
        raise HaltedByDryRun()
    if not await is_taskforce_still_pending_starter(ewms_rc, taskforce_uuid):
        LOGGER.critical(
            f"Startup Aborted - taskforce is no longer pending-starter: {taskforce_uuid}"
        )
        raise TaskforceNoLongerPendingStarter()

    # submit
    submit_result_obj = submit(
        schedd_obj=schedd_obj,
        n_workers=n_workers,
        submit_dict=submit_dict,
    )

    # assemble attrs for EWMS
    ewms_taskforce_attrs = dict(
        cluster_id=submit_result_obj.cluster(),
        n_workers=submit_result_obj.num_procs(),
        submit_dict=submit_dict,
        job_event_log_fpath=submit_dict["log"],
    )
    return ewms_taskforce_attrs
