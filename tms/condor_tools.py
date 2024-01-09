"""Util functions wrapping common htcondor actions."""


import logging
from typing import TypedDict

import htcondor  # type: ignore[import-untyped]
from typing_extensions import Required  # Required new to py3.11

LOGGER = logging.getLogger(__name__)


# from https://github.com/htcondor/htcondor/blob/main/src/condor_scripts/condor_watch_q#L1179
JOB_EVENT_STATUS_TRANSITIONS = {
    htcondor.JobEventType.SUBMIT: htcondor.JobStatus.IDLE,
    htcondor.JobEventType.JOB_EVICTED: htcondor.JobStatus.IDLE,
    htcondor.JobEventType.JOB_UNSUSPENDED: htcondor.JobStatus.IDLE,
    htcondor.JobEventType.JOB_RELEASED: htcondor.JobStatus.IDLE,
    htcondor.JobEventType.SHADOW_EXCEPTION: htcondor.JobStatus.IDLE,
    htcondor.JobEventType.JOB_RECONNECT_FAILED: htcondor.JobStatus.IDLE,
    htcondor.JobEventType.JOB_TERMINATED: htcondor.JobStatus.COMPLETED,
    htcondor.JobEventType.EXECUTE: htcondor.JobStatus.RUNNING,
    htcondor.JobEventType.JOB_HELD: htcondor.JobStatus.HELD,
    htcondor.JobEventType.JOB_SUSPENDED: htcondor.JobStatus.SUSPENDED,
    htcondor.JobEventType.JOB_ABORTED: htcondor.JobStatus.REMOVED,
}


class HoldReason(TypedDict, total=False):
    message: Required[str]
    subcode_lookup: dict[int, str]
    subcode_meaning: str


HOLD_REASON_LOOKUP: dict[int, HoldReason] = {
    1: {
        "message": "The user put the job on hold with condor_hold",
    },
    3: {
        "message": "The PERIODIC_HOLD expression evaluated to True. Or, ON_EXIT_HOLD was true",
        "subcode_meaning": "User Specified",
    },
    4: {
        "message": "The credentials for the job are invalid",
    },
    5: {
        "message": "A job policy expression evaluated to Undefined",
    },
    6: {
        "message": "The condor_starter failed to start the executable",
        "subcode_meaning": "Errno",
    },
    7: {
        "message": "The standard output file for the job could not be opened",
        "subcode_meaning": "Errno",
    },
    8: {
        "message": "The standard input file for the job could not be opened",
        "subcode_meaning": "Errno",
    },
    9: {
        "message": "The standard output stream for the job could not be opened",
        "subcode_meaning": "Errno",
    },
    10: {
        "message": "The standard input stream for the job could not be opened",
        "subcode_meaning": "Errno",
    },
    11: {
        "message": "An internal HTCondor protocol error was encountered when transferring files"
    },
    12: {
        "message": "An error occurred while transferring job output files or self-checkpoint files",
        "subcode_meaning": "Errno or plug-in error",
    },
    13: {
        "message": "An error occurred while transferring job input files",
        "subcode_meaning": "Errno or plug-in error",
    },
    14: {
        "message": "The initial working directory of the job cannot be accessed",
        "subcode_meaning": "Errno",
    },
    15: {
        "message": "The user requested the job be submitted on hold",
    },
    16: {
        "message": "Input files are being spooled",
    },
    17: {
        "message": "A standard universe job is not compatible with the condor_shadow version available on the submitting machine"
    },
    18: {
        "message": "An internal HTCondor protocol error was encountered when transferring files"
    },
    19: {
        "message": "<Keyword>_HOOK_PREPARE_JOB was defined but could not be executed or returned failure"
    },
    20: {
        "message": "The job missed its deferred execution time and therefore failed to run"
    },
    21: {
        "message": "The job was put on hold because WANT_HOLD in the machine policy was true"
    },
    22: {
        "message": "Unable to initialize job event log",
    },
    23: {
        "message": "Failed to access user account",
    },
    24: {
        "message": "No compatible shadow",
    },
    25: {
        "message": "Invalid cron settings",
    },
    26: {
        "message": "SYSTEM_PERIODIC_HOLD evaluated to true",
    },
    27: {
        "message": "The system periodic job policy evaluated to undefined",
    },
    32: {
        "message": "The maximum total input file transfer size was exceeded. (See MAX_TRANSFER_INPUT_MB)"
    },
    33: {
        "message": "The maximum total output file transfer size was exceeded. (See MAX_TRANSFER_OUTPUT_MB)"
    },
    34: {
        "message": "Memory usage exceeds a memory limit",
    },
    35: {
        "message": "Specified Docker image was invalid",
    },
    36: {
        "message": "Job failed when sent the checkpoint signal it requested",
    },
    37: {
        "message": "User error in the EC2 universe",
        "subcode_lookup": {
            1: "Public key file not defined",
            2: "Private key file not defined",
            4: "Grid resource string missing EC2 service URL",
            9: "Failed to authenticate",
            10: "Can’t use existing SSH keypair with the given server’s type",
            20: "You, or somebody like you, cancelled this request",
        },
    },
    38: {
        "message": "Internal error in the EC2 universe",
        "subcode_lookup": {
            3: "Grid resource type not EC2",
            5: "Grid resource type not set",
            7: "Grid job ID is not for EC2",
            21: "Unexpected remote job status",
        },
    },
    39: {
        "message": "Adminstrator error in the EC2 universe",
        "subcode_lookup": {
            6: "EC2_GAHP not defined",
        },
    },
    40: {
        "message": "Connection problem in the EC2 universe",
        "subcode_lookup": {
            11: "while creating an SSH keypair",
            12: "while starting an on-demand instance",
            17: "while requesting a spot instance",
        },
    },
    41: {
        "message": "Server error in the EC2 universe",
        "subcode_lookup": {
            13: "Abnormal instance termination reason",
            14: "Unrecognized instance termination reason",
            22: "Resource was down for too long",
        },
    },
    42: {
        "message": "Instance potentially lost due to an error in the EC2 universe",
        "subcode_lookup": {
            15: "Connection error while terminating an instance",
            16: "Failed to terminate instance too many times",
            17: "Connection error while terminating a spot request",
            18: "Failed to terminated a spot request too many times",
            19: "Spot instance request purged before instance ID acquired",
        },
    },
    43: {
        "message": "Pre script failed",
    },
    44: {
        "message": "Post script failed",
    },
    45: {
        "message": "Test of singularity runtime failed before launching a job",
    },
    46: {
        "message": "The job’s allowed duration was exceeded",
    },
    47: {
        "message": "The job’s allowed execution time was exceeded",
    },
    48: {
        "message": "Prepare job shadow hook failed when it was executed; status code indicated job should be held"
    },
}


def hold_reason_to_string(code: int | None, subcode: int | None) -> str:
    """Get a human-readable message from the hold code (and subcode)."""
    try:
        hold_info = HOLD_REASON_LOOKUP[code]
    except ValueError:
        raise ValueError(f"Unknown Hold Reason ({code},{subcode})")

    if subcode is not None:
        if "subcode_lookup" in hold_info:
            try:
                subreason = hold_info["subcode_lookup"][subcode]
            except KeyError:
                subreason = str(subcode)
            return f"{hold_info['message']}: {subreason}"
        elif "subcode_meaning" in hold_info:
            return f"{hold_info['message']}: {subcode} ({hold_info['subcode_meaning']})"
        else:
            return f"{hold_info['message']}: {subcode} (unknown)"
    else:
        return hold_info["message"]
