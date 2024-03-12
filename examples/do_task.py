"""A simple example script to see EWMS pilot in real-time.

See https://github.com/Observation-Management-Service/ewms-workflow-management-service/blob/main/examples/request_task.py
"""


import argparse
import asyncio
import logging
import os
from pathlib import Path

from ewms_pilot import FileType, consume_and_reply

LOGGER = logging.getLogger(__name__)


async def main(
    queue_incoming: str,
    queue_outgoing: str,
    debug_dir: Path,
) -> None:
    """Test a normal .txt-based pilot."""

    await consume_and_reply(
        # task is to double the input, one-at-a-time
        cmd="""python3 -c "
import sys
import time
import argparse
import os
time.sleep(5)
print('this is a log', file=sys.stderr)
time.sleep(5)
output = open('{{INFILE}}').read().strip() * 2
time.sleep(5)
print('printed: ' + output)
print(output, file=open('{{OUTFILE}}','w'))
time.sleep(5)
" """,
        queue_incoming=queue_incoming,
        queue_outgoing=queue_outgoing,
        ftype_to_subproc=FileType.TXT,
        ftype_from_subproc=FileType.TXT,
        debug_dir=debug_dir,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--queue-incoming",
        required=True,
        help="the name of the incoming queue",
    )
    parser.add_argument(
        "--queue-outgoing",
        required=True,
        help="the name of the outgoing queue",
    )
    args = parser.parse_args()

    if not os.getenv("EWMS_PILOT_BROKER_AUTH_TOKEN"):
        raise RuntimeError("EWMS_PILOT_BROKER_AUTH_TOKEN must be given")

    asyncio.run(
        main(
            args.queue_incoming,
            args.queue_outgoing,
            Path("."),
        )
    )
