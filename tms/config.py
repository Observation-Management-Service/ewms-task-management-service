"""config.py."""


import dataclasses as dc
import logging
from pathlib import Path

import htcondor  # type: ignore[import-untyped]
from wipac_dev_tools import from_environment_as_dataclass, logging_tools

WATCHER_N_TOP_TASK_ERRORS = 10
COLLECTOR = htcondor.param["CONDOR_HOST"]
SCHEDD = htcondor.param["FULL_HOSTNAME"]


@dc.dataclass(frozen=True)
class EnvConfig:
    """Environment variables."""

    # pylint:disable=invalid-name

    JOB_EVENT_LOG_DIR: Path
    JOB_EVENT_LOG_MODIFICATION_EXPIRY: int = 60 * 60 * 24

    TMS_OUTER_LOOP_WAIT: int = 60
    TMS_WATCHER_INTERVAL: int = 60 * 3

    EWMS_ADDRESS: str = ""
    EWMS_AUTH: str = ""

    DRYRUN: bool = False
    CI_TEST: bool = False
    LOG_LEVEL: str = "DEBUG"
    LOG_LEVEL_THIRD_PARTY: str = "WARNING"


ENV = from_environment_as_dataclass(EnvConfig)


def config_logging() -> None:
    """Configure the logging level and format.

    This is separated into a function for consistency between app and
    testing environments.
    """
    hand = logging.StreamHandler()
    hand.setFormatter(
        logging.Formatter(
            "%(asctime)s.%(msecs)03d [%(levelname)8s] %(name)s[%(process)d] %(message)s <%(filename)s:%(lineno)s/%(funcName)s()>",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logging.getLogger().addHandler(hand)
    logging_tools.set_level(
        ENV.LOG_LEVEL,  # type: ignore[arg-type]
        first_party_loggers=__name__.split(".", maxsplit=1)[0],
        third_party_level=ENV.LOG_LEVEL_THIRD_PARTY,  # type: ignore[arg-type]
        future_third_parties=[],
    )
