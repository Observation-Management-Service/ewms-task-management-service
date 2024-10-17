"""For starting EWMS taskforce workers on an HTCondor cluster."""

import logging
from pathlib import Path
from typing import Any

import htcondor  # type: ignore[import-untyped]
import humanfriendly
from rest_tools.client import RestClient

from ..condor_tools import get_collector, get_schedd
from ..config import ENV, WMS_ROUTE_VERSION_PREFIX
from ..utils import LogFileLogic

LOGGER = logging.getLogger(__name__)


def get_output_dpath_macro_template(taskforce_uuid: str) -> Path:
    """Assemble the path for the output directory."""
    return (
        ENV.JOB_EVENT_LOG_DIR / f"ewms-taskforce-{taskforce_uuid}-cluster-$(ClusterId)"
    )


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
        f"/{WMS_ROUTE_VERSION_PREFIX}/taskforces/{taskforce_uuid}",
    )
    return ret["phase"] == "pending-starter"  # type: ignore[no-any-return]


def make_condor_job_description(
    taskforce_uuid: str,
    # pilot_config
    pilot_image: str,
    pilot_environment: dict[str, Any],
    pilot_input_files: list[str],
    # worker_config
    do_transfer_worker_stdouterr: bool,
    max_worker_runtime: int,
    n_cores: int,
    priority: int,
    worker_disk: int | str,
    worker_memory: int | str,
) -> tuple[dict[str, Any], bool]:
    """Make the condor job description (dict).

    Return the job description along with a bool of whether to make the
    output subdir.
    """

    # NOTE:
    # In the newest version of condor we could use:

    # But for now, we're stuck with:
    #   executable = ...
    #   +SingularityImage = ...
    #   arguments = /usr/local/icetray/env-shell.sh python -m ...
    # Because "this universe doesn't know how to do the
    #   entrypoint, and loading the icetray env file
    #   directly from cvmfs messes up the paths" -DS

    # update environment
    # order of precedence (descending): WMS's values, runtime-specific, constant
    pilot_envvar_defaults = {
        # constant
        "EWMS_PILOT_HTCHIRP": "True",
        "EWMS_PILOT_HTCHIRP_DEST": "JOB_EVENT_LOG",
        # runtime-specific (from user)
        **{
            k: v
            for k, v in ENV.TMS_ENV_VARS_AND_VALS_ADD_TO_PILOT.items()
            # prevent the user from defining env vars that could have adverse effects
            if k.startswith("EWMS_PILOT_")
        },
    }
    for k, v in pilot_envvar_defaults.items():
        pilot_environment.setdefault(k, v)  # does not override

    def to_envval(val: Any) -> str:
        """Convert an arbitrary value to a string to be used as an environment variable."""
        if isinstance(val, list):
            # this is used by the pilot for handling multiple queues
            # WMS makes lists for:
            #    EWMS_PILOT_QUEUE_INCOMING / EWMS_PILOT_QUEUE_OUTGOING
            #    EWMS_PILOT_QUEUE_*_AUTH_TOKEN
            #    EWMS_PILOT_QUEUE_*_BROKER_TYPE
            #    EWMS_PILOT_QUEUE_*_BROKER_ADDRESS
            out_val = ";".join(val)
        else:
            out_val = str(val)
        if " " in out_val:
            out_val = f"'{out_val}'"  # quote it
        out_val = out_val.replace("\n", " ")  # no new-lines!
        return out_val

    # write

    # worker stdout & stderr
    submit_dict = {
        "universe": "container",
        "+should_transfer_container": "no",
        "container_image": f"{ENV.CVMFS_PILOT_PATH}:{pilot_image.lstrip('v')}",  # not quoted -- otherwise condor assumes relative path
        #
        "arguments": "",  # NOTE: args were removed in https://github.com/Observation-Management-Service/ewms-workflow-management-service/pull/38  # pilot_arguments.replace('"', r"\""),  # escape embedded quotes
        "environment": f'"{" ".join(f"{k}={to_envval(v)}" for k, v in sorted(pilot_environment.items()))}"',  # must be quoted
        #
        "Requirements": (
            "ifthenelse(!isUndefined(HAS_SINGULARITY), HAS_SINGULARITY, HasSingularity) && "
            "HAS_CVMFS_icecube_opensciencegrid_org && "
            # "has_avx && has_avx2 && "
            'OSG_OS_VERSION =?= "8"'  # support apptainer-in-apptainer https://github.com/apptainer/apptainer/issues/2167
        ),
        "+FileSystemDomain": '"blah"',  # must be quoted
        #
        # cluster logs -- shared w/ other clusters
        "log": str(LogFileLogic.make_log_file_name()),
        #
        "transfer_input_files": f'"{" ".join(pilot_input_files)}"',  # must be quoted
        "transfer_output_files": "",  # TODO: add ewms-pilot debug directory
        # https://htcondor.readthedocs.io/en/latest/users-manual/file-transfer.html#specifying-if-and-when-to-transfer-files
        "should_transfer_files": "YES",
        "when_to_transfer_output": "ON_EXIT_OR_EVICT",
        #
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
        #
        "priority": int(priority),
        "+WantIOProxy": "true",  # for HTChirp
        "+OriginalTime": max_worker_runtime,  # Execution time limit -- 1 hour default on OSG
        #
        "+EWMSTaskforceUUID": f'"{taskforce_uuid}"',  # must be quoted
        "job_ad_information_attrs": "EWMSTaskforceUUID",
    }
    if do_transfer_worker_stdouterr:
        # this is the location where the files will go when/if *returned here*
        submit_dict.update(
            {
                "output": str(
                    get_output_dpath_macro_template(taskforce_uuid) / "$(ProcId).out"
                ),
                "error": str(
                    get_output_dpath_macro_template(taskforce_uuid) / "$(ProcId).err"
                ),
            }
        )

    LOGGER.info(submit_dict)
    return (
        submit_dict,
        do_transfer_worker_stdouterr,  # NOTE: in future, this could be a compound conditional
    )


def submit(
    schedd_obj: htcondor.Schedd,
    n_workers: int,
    submit_dict: dict[str, Any],
) -> tuple[int, int]:
    """Start taskforce on Condor cluster."""
    submit_obj = htcondor.Submit(submit_dict)

    LOGGER.info("This submit object will be submitted:")
    LOGGER.info(submit_obj)

    # submit
    LOGGER.info("Submitting request to condor...")
    submit_result_obj = schedd_obj.submit(
        submit_obj,
        count=n_workers,  # submit N workers
    )
    cluster_id, num_procs = submit_result_obj.cluster(), submit_result_obj.num_procs()
    LOGGER.info(f"SUCCESS: Submitted request to condor ({cluster_id=}, {num_procs=}).")

    LOGGER.info("This submit classad has been submitted:")
    LOGGER.info(submit_result_obj)

    return cluster_id, num_procs


async def start(
    schedd_obj: htcondor.Schedd,
    ewms_rc: RestClient,
    #
    taskforce_uuid: str,
    n_workers: int,
    # pilot_config
    pilot_image: str,
    pilot_environment: dict[str, Any],
    pilot_input_files: list[str],
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
    submit_dict, do_make_output_subdir = make_condor_job_description(
        taskforce_uuid,
        #
        pilot_image,
        pilot_environment,
        pilot_input_files,
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
    cluster_id, num_procs = submit(  # -> htcondor.HTCondorInternalError (let it raise)
        schedd_obj=schedd_obj,
        n_workers=n_workers,
        submit_dict=submit_dict,
    )

    # make output subdir?
    # we have to construct AFTER 'submit' b/c the cluster id is not known prior
    if do_make_output_subdir:
        output_subdir = Path(
            str(get_output_dpath_macro_template(taskforce_uuid)).replace(
                "$(ClusterId)",
                str(cluster_id),
            )
        )
        output_subdir.mkdir(parents=True, exist_ok=True)

    # assemble attrs for EWMS
    ewms_taskforce_attrs = dict(
        cluster_id=cluster_id,
        n_workers=num_procs,
        submit_dict=submit_dict,
        job_event_log_fpath=submit_dict["log"],
    )
    return ewms_taskforce_attrs
