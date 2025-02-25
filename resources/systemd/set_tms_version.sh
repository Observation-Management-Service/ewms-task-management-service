#!/bin/bash
set -euo pipefail

# Redirects the image symlink to a different version on CVMFS

if [[ "$(basename "$PWD")" != "tms" && "$(basename "$PWD")" != "tms-dev" ]]; then
    echo "Error: Expected to be in 'tms' or 'tms-dev', but currently in: $PWD"
    exit 1
fi


if [[ -z "$1" ]]; then
    echo "Error: Missing argument. Usage: $0 TMS_IMAGE_TAG"
    exit 1
fi
tms_image_tag="$1"

cvmfs_base="/cvmfs/icecube.opensciencegrid.org/containers/ewms/observation-management-service/ewms-task-management-service"

full_image_path="$cvmfs_base:$tms_image_tag"

# Check if the image directory exists
if [[ ! -d "$full_image_path" ]]; then
    echo "Error: Image not found on CVMFS: $full_image_path"
    exit 2
fi

# Ensure symlink update works
ln -snf "$full_image_path" "./apptainer_container_symlink"

# Touch envfile so systemd restarts the app
touch "./envfile"

echo "Successfully updated symlink to: $full_image_path"
