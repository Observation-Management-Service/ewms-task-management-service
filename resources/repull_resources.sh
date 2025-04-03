#!/bin/bash
set -euo pipefail

URL="https://github.com/Observation-Management-Service/ewms-task-management-service/archive/refs/heads/main.tar.gz"
SOURCE_PATH="ewms-task-management-service-main/resources"
DEST="/home/ewms/resources"

mkdir -p "$DEST"

curl -L "$URL" | tar -xz \
    -C "$DEST" \
    --strip-components="$(echo "$SOURCE_PATH" | awk -F/ '{print NF}')" \
    --exclude='*/systemd/tms-*/envfile' \
    --exclude='*/systemd/tms-*/apptainer_container_symlink' \
    "$SOURCE_PATH"

# NOTE the --exclude flags are technically not needed since these files are not in the github repo
