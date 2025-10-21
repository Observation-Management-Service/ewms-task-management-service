"""Monitor and process files according to specified actions every 60 seconds."""

import asyncio
import glob
import logging
import os
import shutil
import tarfile
import time
from functools import partial
from pathlib import Path
from typing import Awaitable, Callable

from rest_tools.client import RestClient

from ..config import ENV
from ..utils import JELFileLogic, TaskforceDirLogic

LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Action helpers (can be passed directly or via functools.partial/lambda)
# -----------------------------------------------------------------------------


def action_rm(fpath: Path) -> None:
    """rm the file/dir."""
    if not fpath.exists():
        LOGGER.info(f"skip: already absent {fpath}")
        return

    if fpath.is_dir():
        shutil.rmtree(fpath)
    else:
        os.remove(fpath)

    LOGGER.info(f"done: rm {fpath}")


def action_mv(fpath: Path, *, dest: Path) -> None:
    """mv the file/dir (bash semantics)."""
    if not dest:
        raise RuntimeError(f"destination not given for 'mv' on {fpath=}")

    if dest.exists():
        if dest.is_dir():
            final = dest / fpath.name
        else:
            final = dest  # overwrite permitted (bash-like)
    else:
        # missing dest → treat as rename; do NOT create parent dirs
        final = dest

    shutil.move(str(fpath), str(final))
    LOGGER.info(f"done: mv {fpath} → {final}")


def action_tar_gz(fpath: Path, *, dest: Path) -> None:
    """
    Tar+gzip the directory and remove the source afterwards (atomically).

    Steps:
    1. Create parent 'dest' directory if needed.
    2. Write tar.gz to a temporary file (same filesystem).
    3. Atomically rename temp → final archive using os.replace().
    4. Remove original directory if archive was successfully created.
    """
    if not dest:
        raise RuntimeError(f"destination not given for 'tar_gz' on {fpath=}")
    if not fpath.is_dir():
        raise NotADirectoryError(f"{fpath=}")

    # Example: /archive_dir/my-taskforce.tar.gz
    final_tar = dest / f"{fpath.name}.tar.gz"
    # Temp file in same dir for atomic replace
    temp_tar = dest / f".{fpath.name}.tar.gz.tmp"

    if final_tar.exists():
        raise FileExistsError(f"archive already exists: {final_tar}")

    dest.mkdir(parents=True, exist_ok=True)

    try:
        # Write to a temporary tar.gz first
        with tarfile.open(temp_tar, "w:gz") as tar:
            tar.add(fpath, arcname=fpath.name)  # keep top-level dir structure

        # Atomically move temp → final
        os.replace(temp_tar, final_tar)

        # Now that archive is safely in place, delete original directory
        shutil.rmtree(fpath)
        LOGGER.info(f"done: tar.gz {fpath} → {final_tar} + rm {fpath}")

    except Exception:
        # If something failed before the atomic rename, ensure temp is removed
        if temp_tar.exists():
            try:
                temp_tar.unlink()
            except Exception:
                pass
        raise


# -----------------------------------------------------------------------------
# FileManager
# -----------------------------------------------------------------------------


class FileManager:
    """What action to take on the filepath."""

    def __init__(
        self,
        fpattern: str,
        action: Callable[[Path], None],
        age_threshold: int,
        precheck_async: Callable[[Path], Awaitable[bool]] | None = None,
    ):
        self.fpattern = fpattern
        self.action = action
        self.age_threshold = age_threshold  # Only act if file is older than this
        self.precheck_async = precheck_async

    def is_old_enough(self, fpath: Path) -> bool:
        """Is the file/dir older than the age_threshold?"""
        threshold_time = time.time() - self.age_threshold

        if fpath.is_dir():

            # Walk through files; if any are newer than threshold -> not old enough
            for p in fpath.rglob("*"):
                # short circuit logic (don't traverse more than needed)
                try:
                    if p.is_file() and p.stat().st_mtime > threshold_time:
                        return False
                except FileNotFoundError:
                    continue

            # Notes:
            #   - If the dir had no files *OR* had only old files, check dir's mtime.
            #   - A dir's mtime updates when its entries change (create/rm/mv files or subdirs),
            #       *NOT* when the contents of its descendants change.
            try:
                return fpath.stat().st_mtime <= threshold_time
            except FileNotFoundError:
                return False

        # Plain file (or symlink to a file)
        else:
            try:
                return fpath.stat().st_mtime <= threshold_time
            except FileNotFoundError:
                return False

    async def act(self, fpath: Path) -> bool:
        """Perform action on filepath, if the file is old enough."""
        if not fpath.exists():
            LOGGER.info(f"ok: file deleted/moved before action ({self.action})")
            return False

        # age check
        if not self.is_old_enough(fpath):
            LOGGER.debug(
                f"no action -- filepath not older than {self.age_threshold} seconds {fpath=}"
            )
            return False

        # do potentially expensive check after cheap age check
        if self.precheck_async is not None:
            if not await self.precheck_async(fpath):
                LOGGER.debug(f"precheck returned 'False' for {fpath=}")
                return False

        # act
        LOGGER.info(f"performing action {self.action} on {fpath}")
        self.action(fpath)
        return True


# -----------------------------------------------------------------------------
# File Managers
# -----------------------------------------------------------------------------


def build_file_managers(ewms_rc: RestClient) -> list[FileManager]:
    """Build the list of file managers."""
    return [
        #
        # ex: 2025-8-26.tms.jel
        # -> does check if no noncompleted taskforces
        FileManager(
            str(JELFileLogic.parent / f"*{JELFileLogic.extension}"),
            action=action_rm,
            age_threshold=ENV.JOB_EVENT_LOG_MODIFICATION_EXPIRY_SHORT,
            precheck_async=partial(
                JELFileLogic.has_no_noncompleted_taskforces, ewms_rc
            ),
        ),
        #
        # ex: 2025-8-26.tms.jel
        # -> does *NOT* check if no noncompleted taskforces
        FileManager(
            str(JELFileLogic.parent / f"*{JELFileLogic.extension}"),
            action=action_rm,
            age_threshold=ENV.JOB_EVENT_LOG_MODIFICATION_EXPIRY_LONG,
        ),
        #
        # ex: ewms-taskforce-TF-685e6219-e85461b3-f8dc0d3c-6e4a5d72
        FileManager(
            str(TaskforceDirLogic.parent / f"{TaskforceDirLogic.prefix}*"),
            action=partial(action_tar_gz, dest=ENV.JOB_EVENT_LOG_DIR),
            age_threshold=ENV.TASKFORCE_DIRS_EXPIRY,
        ),
        #
        # ex: ewms-taskforce-TF-685e6219-e85461b3-f8dc0d3c-6e4a5d72.tar.gz
        FileManager(
            str(TaskforceDirLogic.parent / f"{TaskforceDirLogic.prefix}*.tar.gz"),
            action=action_rm,
            age_threshold=ENV.TASKFORCE_DIRS_TAR_EXPIRY,
        ),
    ]


# -----------------------------------------------------------------------------
# Runner
# -----------------------------------------------------------------------------


async def run_once(
    ewms_rc: RestClient,
    file_managers: list[FileManager] | None = None,
) -> int:
    """
    Execute a single inspection pass over all file managers.

    Returns:
        int: number of actions performed in this pass.
    """
    if file_managers is None:
        file_managers = build_file_managers(ewms_rc)

    LOGGER.info("inspecting filepaths...")
    n_actions = 0

    for fm in file_managers:
        LOGGER.debug(f"searching filepath pattern: {fm.fpattern}")

        for p in glob.iglob(fm.fpattern):  # streaming
            fpath = Path(p)
            LOGGER.debug(f"looking at {fpath=}")
            try:
                n_actions += int(await fm.act(fpath))  # bool -> 1/0
            except Exception:
                LOGGER.exception(f"action failed for {fpath=}")
                continue
            else:
                # let the TMS do other scheduled things
                await asyncio.sleep(0)

    LOGGER.info(f"done inspecting filepaths -- performed {n_actions} actions")
    return n_actions


async def run(ewms_rc: RestClient) -> None:
    """Run the file manager loop.

    NOTE - waits 'TMS_FILE_MANAGER_INTERVAL' seconds at top
    """
    LOGGER.info("Activated.")
    file_managers = build_file_managers(ewms_rc)

    while True:
        LOGGER.info(f"next round in {ENV.TMS_FILE_MANAGER_INTERVAL}s")
        await asyncio.sleep(ENV.TMS_FILE_MANAGER_INTERVAL)  # O(hours)
        await run_once(ewms_rc, file_managers)
