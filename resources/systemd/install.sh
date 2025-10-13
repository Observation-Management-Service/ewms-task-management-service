#!/bin/bash
set -euo pipefail

# --------------------------------------------------------------------------------------
# Install systemd unit files to user systemd
#
# Usage: ./install_units.sh <unit-subdir>
# --------------------------------------------------------------------------------------

if [[ -z "${1:-}" ]]; then
    echo "Usage: $0 <TMS_PROD_DIRPATH|TMS_DEV_DIRPATH>" >&2
    exit 1
else
    UNIT_SUBDIR="$1"
    UNIT_SUBDIR=$(realpath "$UNIT_SUBDIR")
    UNIT_SUBDIR="${UNIT_SUBDIR%/}"  # remove trailing slash, if present
fi

if [[ "$(basename "$UNIT_SUBDIR")" != "tms-prod" && "$(basename "$UNIT_SUBDIR")" != "tms-dev" ]]; then
    echo "ERROR: unit subdir must be 'tms-prod' or 'tms-dev', not '$UNIT_SUBDIR'"
    exit 1
fi

SYSTEMD_INSTALL_DIR="$HOME/.config/systemd/user"

########################################################################################
# validate

if [[ ! -d "$UNIT_SUBDIR" ]]; then
    echo "ERROR: '$UNIT_SUBDIR' does not exist or is not a directory." >&2
    exit 2
fi

# required support files
if [[ ! -f "$UNIT_SUBDIR/envfile" ]]; then
    echo "Missing file: envfile" >&2
    exit 2
fi
if [[ ! -L "$UNIT_SUBDIR/apptainer_container_symlink" ]]; then
    echo "Missing symlink: apptainer_container_symlink" >&2
    exit 2
fi


########################################################################################
# prep

set -x
mkdir -p "$SYSTEMD_INSTALL_DIR"

# cp: don't overwrite existing ones or symlinks
cp -ux "$UNIT_SUBDIR"/*.service "$UNIT_SUBDIR"/*.path "$SYSTEMD_INSTALL_DIR"

systemctl --user daemon-reload  # reload systemd to recognize new/updated unit files
set +x


########################################################################################
# ensure log directories exist (for append:/ paths)

logdir="/scratch/ewms/$(basename "$UNIT_SUBDIR")/logs/"
unit_file="$UNIT_SUBDIR/ewms-$(basename "$UNIT_SUBDIR").service"
if grep -q "$logdir" "$unit_file"; then
    if [[ ! -d "$logdir" ]]; then
        mkdir -p "$logdir"
    fi
else
    echo "ERROR: $logdir not referenced in $unit_file"
    exit 2
fi

########################################################################################
# enable & (re)start unit files

for unit_fpath in "$UNIT_SUBDIR"/*; do
    UNIT=$(basename "$unit_fpath")

    # only process *.service and *.path files
    if [[ "$UNIT" != *.service && "$UNIT" != *.path ]]; then
        echo "Skipping unsupported file: $UNIT"
        continue
    fi

    # enable
    set -x
    systemctl --user enable "$UNIT"
    set +x
    if systemctl --user show "$UNIT" --property=UnitFileState | grep -q '=enabled'; then
        echo "$UNIT: enabled"
    else
        echo "$UNIT: failed to enable"
        exit 3
    fi

    # restart if running, otherwise start
    if systemctl --user is-active --quiet "$UNIT"; then
        # ^^^ always false for 'oneshot' units, that's ok
        echo "$UNIT: restarting"
        set -x
        systemctl --user restart "$UNIT"
        set +x
        echo "$UNIT: restarted"
    else
        # start new unit
        echo "$UNIT: starting"
        set -x
        systemctl --user start "$UNIT"
        set +x

        if [[ "$(systemctl --user show "$UNIT" --property=Result --value)" == "success" ]]; then
            echo "$UNIT: started"
        else
            echo "$UNIT: failed to start"
            exit 4
        fi
    fi
done
echo "All unit files re/started!"

########################################################################################
# dump status of all units

echo
set -x
systemctl --user status ewms* || true
