"""For starting EWMS taskforce workers on an HTCondor cluster."""

import logging
import shlex
from pathlib import Path
from typing import Any

import htcondor  # type: ignore[import-untyped]
import humanfriendly
from rest_tools.client import RestClient

from ..condor_tools import get_collector, get_schedd
from ..config import (
    DEFAULT_CONDOR_REQUIREMENTS,
    ENV,
    WMS_URL_V_PREFIX,
)
from ..utils import JELFileLogic, TaskforceDirLogic

LOGGER = logging.getLogger(__name__)


class HaltedByDryRun(Exception):
    """Raise when doing a dry run and no further progress is needed."""


class TaskforceNotToBeStarted(Exception):
    """Raise when the taskforce is no longer intended to start as previously expected."""


async def is_taskforce_still_pending_starter(
    ewms_rc: RestClient,
    taskforce_uuid: str,
) -> bool:
    """Return whether the taskforce is still pending-starter."""
    ret = await ewms_rc.request(
        "GET",
        f"/{WMS_URL_V_PREFIX}/taskforces/{taskforce_uuid}",
    )
    return ret["phase"] == "pending-starter"  # type: ignore[no-any-return]


def write_envfile(taskforce_uuid: str, env_vars: dict) -> Path:
    """Construct the envfile to be transferred."""
    envfile = (
        Path(TaskforceDirLogic.create(taskforce_uuid)) / "ewms_htcondor_envfile.sh"
    )

    def to_envval(val: Any) -> str:
        """Convert an arbitrary value to a string to be used as an environment variable."""
        out_val = str(val)  # just in case this slipped past the value typechecking
        out_val = out_val.replace("\n", " ")  # no new-lines!
        out_val = shlex.quote(out_val)  # escape special chars
        return out_val

    # make file
    with open(envfile, "w") as f:
        f.write("#!/bin/bash\n\n")

        # header comment
        f.write("# Environment setup for HTCondor worker\n")
        f.write(
            "# This file is auto-generated and sets necessary environment variables.\n"
        )
        f.write("# Sourced automatically by the EWMS Pilot's container entrypoint.\n\n")

        f.write("set -x\n")  # enable command tracing
        # Write environment variables
        for key, value in sorted(env_vars.items()):
            f.write(f"export {key}={to_envval(value)}\n")
        f.write("set +x\n")  # disable command tracing

        # footer comment
        f.write("\n# End of environment file\n")

    # make the file executable
    envfile.chmod(0o755)  # execute permissions

    return envfile


def assemble_pilot_fully_qualified_image(image_source: str, tag: str) -> str:
    """Get the fully qualified image name/location for the pilot.

    Ex: /cvmfs/icecube.opensciencegrid.org/containers/ewms/observation-management-service/ewms-pilot:v1.2.3
    """
    pilot_image_sources = {
        "auto": ENV.CVMFS_PILOT_PATH,
        "cvmfs": ENV.CVMFS_PILOT_PATH,
        # FUTURE DEV: more sources?
    }
    return f"{pilot_image_sources[image_source.lower()]}:{tag}"


def make_condor_job_description(
    taskforce_uuid: str,
    pilot_config: dict,
    worker_config: dict,
) -> tuple[dict[str, Any], Path | None]:
    """Make the condor job description (dict).

    Return the job description along with the output subdir (or None).
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
        pilot_config["environment"].setdefault(k, v)  # does not override
    envfile = write_envfile(taskforce_uuid, pilot_config["environment"])
    pilot_config["input_files"].append(str(envfile))

    # assemble requirements string
    if worker_config["condor_requirements"].strip():
        all_reqs_str = f"{DEFAULT_CONDOR_REQUIREMENTS} && ({worker_config['condor_requirements'].strip()})"
    else:
        all_reqs_str = DEFAULT_CONDOR_REQUIREMENTS

    # assemble submit dict
    submit_dict = {
        "universe": "container",
        "+should_transfer_container": "no",
        "container_image": assemble_pilot_fully_qualified_image(  # not quoted -- otherwise condor assumes relative path
            pilot_config["image_source"],
            pilot_config["tag"],
        ),
        #
        # "arguments": "",  # NOTE: args were removed in https://github.com/Observation-Management-Service/ewms-workflow-management-service/pull/38  # pilot_arguments.replace('"', r"\""),  # escape embedded quotes
        # "environment": "",  # NOTE: use envfile instead
        #
        "Requirements": all_reqs_str,
        "+FileSystemDomain": '"blah"',  # must be quoted
        #
        # cluster logs -- shared w/ other clusters
        "log": str(JELFileLogic.create_path()),
        #
        "transfer_input_files": ",".join(pilot_config["input_files"]),
        "transfer_output_files": "",  # TODO: add ewms-pilot debug directory
        # https://htcondor.readthedocs.io/en/latest/users-manual/file-transfer.html#specifying-if-and-when-to-transfer-files
        "should_transfer_files": "YES",
        "when_to_transfer_output": "ON_EXIT_OR_EVICT",
        #
        "transfer_executable": "false",
        #
        "request_cpus": str(worker_config["n_cores"]),
        # NOTE: condor uses binary sizes but formats like decimal
        "request_memory": humanfriendly.format_size(
            # "1073741824" -> 1073741824 -> "1 GiB" -> "1 GB" (or "3 MB" -> 3221225472 -> "3 MB")
            humanfriendly.parse_size(str(worker_config["worker_memory"]), binary=True),
            binary=True,
        ).replace("i", ""),
        # NOTE: condor uses binary sizes but formats like decimal
        "request_disk": humanfriendly.format_size(
            # "1073741824" -> 1073741824 -> "1 GiB" -> "1 GB" (or "3 MB" -> 3221225472 -> "3 MB")
            humanfriendly.parse_size(str(worker_config["worker_disk"]), binary=True),
            binary=True,
        ).replace("i", ""),
        #
        "priority": int(worker_config["priority"]),
        "+WantIOProxy": "true",  # for HTChirp
        "+OriginalTime": worker_config[
            # Execution time limit -- 1 hour default on OSG
            "max_worker_runtime"
        ],
        #
        "+EWMSTaskforceUUID": f'"{taskforce_uuid}"',  # must be quoted
        "job_ad_information_attrs": "EWMSTaskforceUUID",
    }

    if worker_config["do_transfer_worker_stdouterr"]:
        # this is the location where the files will go when/if *returned here*
        output_subdir = (
            TaskforceDirLogic.create(taskforce_uuid) / "cluster-$(ClusterId)"
        )
        submit_dict.update(
            {
                "output": str(output_subdir / "$(ProcId).out"),
                "error": str(output_subdir / "$(ProcId).err"),
            }
        )
    else:
        output_subdir = None

    LOGGER.debug(submit_dict)
    return submit_dict, output_subdir


def submit(
    schedd_obj: htcondor.Schedd,
    n_workers: int,
    submit_dict: dict[str, Any],
) -> tuple[int, int]:
    """Start taskforce on Condor cluster."""
    submit_obj = htcondor.Submit(submit_dict)

    # submit
    LOGGER.info("Submitting request to condor...")
    LOGGER.info(submit_obj)
    submit_result_obj = schedd_obj.submit(
        submit_obj,
        count=n_workers,  # submit N workers
    )
    cluster_id, num_procs = submit_result_obj.cluster(), submit_result_obj.num_procs()
    LOGGER.info(submit_result_obj)  # includes cluster_id and num_procs

    return cluster_id, num_procs


async def start(
    schedd_obj: htcondor.Schedd,
    ewms_rc: RestClient,
    #
    taskforce_uuid: str,
    n_workers: int,
    pilot_config: dict,
    worker_config: dict,
) -> dict[str, Any]:
    """Start an EWMS taskforce workers on an HTCondor cluster.

    Returns attrs for sending to EWMS.
    """
    LOGGER.info(
        f"Starting {n_workers} EWMS taskforce workers on {get_collector()} / {get_schedd()}"
    )

    # prep
    submit_dict, output_subdir = make_condor_job_description(
        taskforce_uuid,
        pilot_config,
        worker_config,
    )

    # final checks
    if ENV.DRYRUN:
        LOGGER.critical("Startup Aborted - dryrun enabled")
        raise HaltedByDryRun()
    if not await is_taskforce_still_pending_starter(ewms_rc, taskforce_uuid):
        LOGGER.critical(
            f"Startup Aborted - taskforce is no longer pending-starter: {taskforce_uuid}"
        )
        raise TaskforceNotToBeStarted()

    # submit
    cluster_id, num_procs = submit(  # -> htcondor.HTCondorInternalError (let it raise)
        schedd_obj=schedd_obj,
        n_workers=n_workers,
        submit_dict=submit_dict,
    )

    # make output subdir?
    if output_subdir:
        output_subdir = Path(
            str(output_subdir).replace("$(ClusterId)", str(cluster_id))
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
