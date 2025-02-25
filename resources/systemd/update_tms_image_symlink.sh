#!/bin/bash
set -euo pipefail

# ------------------------------------------------------------------------------
# Script Name: update_tms_image_symlink.sh
# Description: Updates the Apptainer container symlink to a specified image
#              version stored on CVMFS.
#
# Usage: ./update_tms_image_symlink.sh TMS_IMAGE_TAG
#
# Arguments:
#   TMS_IMAGE_TAG - The version tag of the TMS image to be used.
#
# Behavior:
#   - Ensures the script is run from either 'tms/' or 'tms-dev/' directory.
#   - Validates that a TMS image tag is provided as an argument.
#   - Checks if the specified image exists on CVMFS.
#   - Updates the symlink to point to the specified image.
#   - Touches `envfile` to trigger a systemd service restart.
#
# Exit Codes:
#   1 - Invalid working directory or missing argument.
#   2 - Specified image version not found on CVMFS.
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
tms_image_tag="$1"

################################################################################
# constants
cvmfs_base="/cvmfs/icecube.opensciencegrid.org/containers/ewms/observation-management-service/ewms-task-management-service"

full_image_path="$cvmfs_base:$tms_image_tag"
if [[ ! -d "$full_image_path" ]]; then
    echo "Error: Image not found on CVMFS: $full_image_path"
    exit 2
fi

################################################################################
# update!

ln -snf "$full_image_path" "./apptainer_container_symlink"

# Touch envfile so systemd restarts the app
touch "./envfile"

echo "Successfully updated symlink to: $full_image_path"
