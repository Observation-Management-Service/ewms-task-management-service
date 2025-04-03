#!/bin/bash
set -euo pipefail

# --------------------------------------------------------------------------------------
# Pull 'resources/' from a GitHub branch into '/home/ewms/resources'
#
# Usage: ./repull_resources.sh [--branch=BRANCH]
# --------------------------------------------------------------------------------------

BRANCH="main"

# parse optional --branch=... arg
for arg in "$@"; do
    case "$arg" in
        --branch=*) BRANCH="${arg#*=}" ;;
        *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
done

URL="https://github.com/Observation-Management-Service/ewms-task-management-service/archive/refs/heads/${BRANCH}.tar.gz"
SOURCE_PATH="ewms-task-management-service-main/resources"
DEST="/home/ewms/resources"

########################################################################################

mkdir -p "$DEST"

curl -L "$URL" | tar -xz \
    -C "$DEST" \
    --strip-components="$(echo "$SOURCE_PATH" | awk -F/ '{print NF}')" \
    --exclude='*/systemd/tms-*/envfile' \
    --exclude='*/systemd/tms-*/apptainer_container_symlink' \
    "$SOURCE_PATH"

# NOTE the --exclude flags are technically not needed since these files are not in the github repo
