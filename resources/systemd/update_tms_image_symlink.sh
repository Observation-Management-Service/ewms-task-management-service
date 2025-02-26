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
#   2 - Specified image version not found on CVMFS.
#   3 - `envfile` is missing, preventing symlink update.
#
# Example:
#   ./update_tms_image_symlink.sh 0.1.52
# ------------------------------------------------------------------------------

################################################################################
# guardrails

# are we in the correct dir?
if [[ "$PWD" != "/home/ewms/tms" && "$PWD" != "/home/ewms/tms-dev" ]]; then
    echo "Error: Expected to be in 'tms' or 'tms-dev', but currently in: $PWD"
    exit 1
fi

# validate args
if [[ -z "$1" ]]; then
    echo "Error: Missing argument. Usage: $0 TMS_IMAGE_TAG"
    exit 1
fi
readonly tms_image_tag="$1"

################################################################################
# constants

readonly cvmfs_base="/cvmfs/icecube.opensciencegrid.org/containers/ewms/observation-management-service/ewms-task-management-service"

readonly full_image_path="$cvmfs_base:$tms_image_tag"
if [[ ! -d "$full_image_path" ]]; then
    echo "Error: Image not found on CVMFS: $full_image_path"
    exit 2
fi

readonly envfile="./envfile"
if [[ ! -f $envfile ]]; then
    echo "Error: './envfile' is missing. Not updating symlink."
    exit 3
fi

################################################################################
# update!

ln -snf "$full_image_path" "./apptainer_container_symlink"

# Touch envfile so systemd restarts the app
touch $envfile

echo "Successfully updated symlink to: $(readlink -f ./apptainer_container_symlink)"
