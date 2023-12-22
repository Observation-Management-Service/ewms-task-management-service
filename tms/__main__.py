"""Entrypoint for TMS."""


import asyncio
import logging

from .config import config_logging
from .starter import starter
from .stopper import stopper
from .watcher import watcher

LOGGER = logging.getLogger(__name__)


def start(args: argparse.Namespace) -> None:
    """Do the action."""
    htcondor.set_subsystem("TOOL")
    htcondor.param["TOOL_DEBUG"] = "D_FULLDEBUG"
    # htcondor.param["TOOL_LOG"] = "log.txt"
    # htcondor.enable_log()
    htcondor.enable_debug()

    # condor auth & go
    with htcondor.SecMan() as secman:
        secman.setToken(htcondor.Token(ENV.CONDOR_TOKEN))
        schedd_obj = condor_tools.get_schedd_obj(args.collector, args.schedd)
        starter.start(args, schedd_obj)


def watch() -> None:
    """explain."""
    watcher.watch(
        args.collector,
        args.schedd,
        submit_result_obj.cluster(),
        schedd_obj,
        submit_result_obj.num_procs(),
        skydriver_rc,
        skydriver_cluster_obj,
    )


async def main() -> None:
    """explain."""


if __name__ == "__main__":
    config_logging()
    asyncio.run(main())
