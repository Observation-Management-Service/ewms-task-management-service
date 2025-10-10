"""config.py."""

import dataclasses as dc
from pathlib import Path
from typing import Dict

from wipac_dev_tools import from_environment_as_dataclass, logging_tools

WATCHER_N_TOP_TASK_ERRORS = 10

WMS_URL_V_PREFIX = "v1"


_BASE_REQUIREMENTS = [
    # singularity support -- note: sub-2 meets this req by default
    "ifthenelse(!isUndefined(HAS_SINGULARITY), HAS_SINGULARITY, HasSingularity)",
    #
    # cvmfs support -- note: sub-2 meets this req by default
    "HAS_CVMFS_icecube_opensciencegrid_org",
    #
    # apptainer-in-apptainer support
    "HasUserNamespaces =?= true",  # should prevent failures w/ "Failed to create user namespace: user namespace disabled"
]
_EXCLUDED_GLIDEIN_SITES = [
    f'GLIDEIN_Site =!= "{site}"'  # '=!=' -> 'not equal or undefined'
    for site in sorted(
        [
            # exclude sites lacking apptainer support:
            # -> mount hook failed
            # "container creation failed: mount hook function failure"
            "San Diego Supercomputer Center",  # 2024-11-08
            "SDSC-PRP",  # 2024-11-08
            "Kansas State University",  # 2025-02-26
            "Rhodes-HPC",  # 2025-04-08
            # -> others
            "AMNH",  # 2025-03-13  # "fuse-overlayfs: cannot mount: No such file or directory"
            "NotreDame",  # 2025-03-13  # "Child exited with exit status 255"
            "SU-ITS",  # 2025-04-11  # "Failed to create user namespace: user namespace disabled"
        ]
    )
]
_EXCLUDED_OSG_SITES = [
    f'OSG_SITE_NAME =!= "{site}"'  # '=!=' -> 'not equal or undefined'
    for site in sorted(
        [
            "Wichita State University",  # 2025-04-16  # AMQPConnectionError
        ]
    )
]
DEFAULT_CONDOR_REQUIREMENTS = " && ".join(
    _BASE_REQUIREMENTS + _EXCLUDED_GLIDEIN_SITES + _EXCLUDED_OSG_SITES
)


@dc.dataclass(frozen=True)
class EnvConfig:
    """Environment variables."""

    # REQUIRED
    EWMS_ADDRESS: str
    EWMS_TOKEN_URL: str
    EWMS_CLIENT_ID: str
    EWMS_CLIENT_SECRET: str
    JOB_EVENT_LOG_DIR: Path

    # OPTIONAL

    # ex: "foo=1 bar=barbar baz=1"
    TMS_ENV_VARS_AND_VALS_ADD_TO_PILOT: Dict[str, str] = dc.field(default_factory=dict)

    JOB_EVENT_LOG_MODIFICATION_EXPIRY: int = 60 * 60 * 24  # 24 hours

    TASKFORCE_DIRS_EXPIRY: int = 60 * 60 * 24 * 5  # 5 days
    TASKFORCE_DIRS_TAR_EXPIRY: int = 60 * 60 * 24 * 5  # 5 days

    TMS_OUTER_LOOP_WAIT: int = 60
    TMS_WATCHER_INTERVAL: int = 60 * 3
    TMS_FILE_MANAGER_INTERVAL: int = 60 * 60 * 1  # 1 hour
    TMS_MAX_LOGGING_INTERVAL: int = (  # something will be logged at least this often
        5 * 60
    )
    TMS_ERROR_WAIT: int = (
        # how much time to wait after an error, with the intention that the error may be transient
        10
    )

    CVMFS_PILOT_PATH: str = (
        "/cvmfs/icecube.opensciencegrid.org/containers/ewms/observation-management-service/ewms-pilot"
    )

    DRYRUN: bool = False
    CI_TEST: bool = False

    LOG_LEVEL: logging_tools.LoggerLevel = "INFO"
    LOG_LEVEL_THIRD_PARTY: logging_tools.LoggerLevel = "WARNING"
    LOG_LEVEL_REST_TOOLS: logging_tools.LoggerLevel = "INFO"


ENV = from_environment_as_dataclass(EnvConfig)


def config_logging() -> None:
    """Configure the logging level and format.

    This is separated into a function for consistency between app and
    testing environments.
    """
    logging_tools.set_level(
        ENV.LOG_LEVEL,
        first_party_loggers=__name__.split(".", maxsplit=1)[0],
        third_party_level=ENV.LOG_LEVEL_THIRD_PARTY,
        future_third_parties=[],
        specialty_loggers={
            "rest_tools": ENV.LOG_LEVEL_REST_TOOLS,
        },
        formatter=logging_tools.WIPACDevToolsFormatter(include_line_location=False),
        utc=True,
    )
