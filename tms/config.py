"""Config settings."""


import dataclasses as dc
import logging
from pathlib import Path

from wipac_dev_tools import from_environment_as_dataclass, logging_tools

WATCHER_INTERVAL = 60 * 3
WATCHER_MAX_RUNTIME = 60 * 60 * 24
WATCHER_N_TOP_TASK_ERRORS = 10


@dc.dataclass(frozen=True)
class EnvConfig:
    """Environment variables."""

    # pylint:disable=invalid-name

    COLLECTOR: str
    SCHEDD: str
    JOB_EVENT_LOG_DIR: Path

    EWMS_ADDRESS: str = ""
    EWMS_AUTH: str = ""
    EWMS_PILOT_QUARANTINE_TIME: int = 0

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
