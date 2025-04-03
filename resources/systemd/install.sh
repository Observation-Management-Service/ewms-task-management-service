#!/bin/bash
set -euo pipefail

# --------------------------------------------------------------------------------------
# Install systemd unit files to user systemd
#
# Usage: ./install_units.sh <unit-subdir>
# --------------------------------------------------------------------------------------

if [[ -z "${1:-}" ]]; then
    echo "Usage: $0 <unit-subdir>" >&2
    exit 1
else
    UNIT_SUBDIR="${1%/}"  # remove trailing slash, if present
fi

SYSTEMD_INSTALL_DIR="$HOME/.config/systemd/user"

########################################################################################
# validate

if [[ ! -d "$UNIT_SUBDIR" ]]; then
    echo "ERROR: '$UNIT_SUBDIR' does not exist or is not a directory." >&2
    exit 2
fi

# required support files
REQUIRED_FILES=( envfile apptainer_container_symlink )
for FILE in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$UNIT_SUBDIR/$FILE" && ! -e "$UNIT_SUBDIR/$FILE" ]]; then
        echo "ERROR: missing required file: $UNIT_SUBDIR/$FILE" >&2
        exit 2
    fi
done

########################################################################################
# prep

mkdir -p "$SYSTEMD_INSTALL_DIR"
cp -ux "$UNIT_SUBDIR"/* "$SYSTEMD_INSTALL_DIR"  # don't overwrite existing ones or symlinks
systemctl --user daemon-reload  # reload systemd to recognize new/updated unit files

########################################################################################
# enable & (re)start unit files

for UNIT_PATH in "$UNIT_SUBDIR"/*; do
    UNIT=$(basename "$UNIT_PATH")

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
        if systemctl --user is-active --quiet "$UNIT"; then
            echo "$UNIT: started"
        else
            echo "$UNIT: failed to start"
            exit 4
        fi
    fi
done
