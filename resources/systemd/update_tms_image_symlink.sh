#!/bin/bash
set -euo pipefail

# ------------------------------------------------------------------------------
# update_tms_image_symlink.sh
#
# Description: Updates the Apptainer container symlink to a specified image
#              version stored on CVMFS.
#
# Usage: ./update_tms_image_symlink.sh TMS_IMAGE_TAG
#
# Arguments:
#   TMS_IMAGE_TAG - The version tag of the TMS image to be used.
#
# Exit Codes:
#   1 - Invalid working directory or missing argument.
#   2 - `envfile` is missing, preventing symlink update.
#   3 - Timed out waiting for specified image version on CVMFS.
#
# Example:
#   ./update_tms_image_symlink.sh 0.1.52
# ------------------------------------------------------------------------------

################################################################################
# guardrails

# are we in the correct dir?
if [[ "$(basename "$PWD")" != "tms-prod" && "$(basename "$PWD")" != "tms-dev" ]]; then
    echo "Error: Expected to be in 'tms-prod' or 'tms-dev', but currently in: $PWD"
    exit 1
fi

# validate args
if [[ -z "${1-}" ]]; then
    echo "Error: Missing argument. Usage: $0 TMS_IMAGE_TAG"
    exit 1
fi
readonly tms_image_tag="$1"

################################################################################
# if 'tms-prod': check for '--dev-too' option

if [[ "$(basename "$PWD")" == "tms-prod" ]]; then
    bonus_dev_update="$(
        python3 -c '
import argparse, sys

p = argparse.ArgumentParser(
    prog="update_tms_image_symlink.sh",
    description="Require --dev-too yes|no when running in tms-prod",
)
p.add_argument(
    "--dev-too",
    dest="dev_too",
    choices=["yes", "no"],
    required=True,
    help="also update ../tms-dev (yes|no)",
)
args = p.parse_args(sys.argv[1:])

if args.dev_too == "yes":
    print("true")
else:
    print("false")
' "${@:2}"
    )" || exit 1
else
    bonus_dev_update="false"
fi

################################################################################
# constants

readonly cvmfs_base="/cvmfs/icecube.opensciencegrid.org/containers/ewms/observation-management-service/ewms-task-management-service"
readonly full_image_path="$cvmfs_base:$tms_image_tag"

################################################################################
# wait for image to exist

readonly sleep_interval=15  # seconds between retries
readonly max_wait_minutes=30  # total wait time in minutes
readonly max_attempts=$((max_wait_minutes * 60 / sleep_interval))

attempt=1
while [[ ! -d "$full_image_path" ]]; do
    echo "Attempt $attempt/$max_attempts: Image not found on CVMFS: $full_image_path"
    if (( attempt >= max_attempts )); then
        echo "Error: Timed out after $max_wait_minutes minutes waiting for image on CVMFS: $full_image_path"
        exit 3
    fi
    echo "-> will retry in $sleep_interval seconds..."
    sleep "$sleep_interval"
    ((attempt++))
done

################################################################################
# function
################################################################################
finalize_update() {
    local _full_image_path="$1"
    local _envfile="./envfile"

    if [[ ! -f "$_envfile" ]]; then
        echo "Error: '${_envfile}' is missing. Not updating symlink."
        exit 2
    fi

    ln -snf "$_full_image_path" "./apptainer_container_symlink"
    touch "$_envfile"  # triggers systemd restart
    echo "Successfully updated symlink in $(basename "$PWD") to: $(readlink -f ./apptainer_container_symlink)"
}

################################################################################
# update symlink here

finalize_update "$full_image_path"

################################################################################
# perform dev update if requested

if [[ "$bonus_dev_update" == "true" ]]; then
    echo "Updating ../tms-dev..."
    (
        cd ../tms-dev
        if ! finalize_update "$full_image_path"; then
            echo "::warning::Failed to update ../tms-dev; prod is updated. Please check logs."
        fi
    )
fi
