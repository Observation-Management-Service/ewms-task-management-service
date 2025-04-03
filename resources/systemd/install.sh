#!/bin/bash
set -euo pipefail

########################################################################################
# install systmed unit files to user systemd
#
# Usage: ./install_units.sh <unit-subdir>
########################################################################################

if [[ -z "${1:-}" ]]; then
    echo "Usage: $0 <unit-subdir>" >&2
    exit 1
else
    UNIT_SUBDIR=$1
fi

SYSTEMD_INSTALL_DIR="$HOME/.config/systemd/user"


########################################################################################
# validate

if [[ ! -d $UNIT_SUBDIR ]]; then
    echo "ERROR: '$UNIT_SUBDIR' does not exist or is not a directory." >&2
    exit 2
fi


########################################################################################
# prep

mkdir -p "$SYSTEMD_INSTALL_DIR"
cp -ux "$UNIT_SUBDIR"/* "$SYSTEMD_INSTALL_DIR"  # don't overwrite existing ones or symlinks
systemctl --user daemon-reload  # reload systemd to recognize new/updated unit files


########################################################################################
# enable unit files

for UNIT_PATH in "$UNIT_SUBDIR"/*; do
    UNIT=$(basename "$UNIT_PATH")
    systemctl --user enable "$UNIT"

    if systemctl --user show "$UNIT" --property=UnitFileState | grep -q '=enabled'; then
        echo "$UNIT: enabled"
    else
        echo "$UNIT: failed to enable"
    fi
done
