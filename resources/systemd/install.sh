#!/bin/bash

# install systmed unit files to user systemd

SYSTEMD_INSTALL_DIR=$HOME/.config/systemd/user/

ENVS=( tms-dev tms-prod )

if [[ ! -d $SYSTEMD_INSTALL_DIR ]]; then
    mkdir -p $SYSTEMD_INSTALL_DIR
fi

for ENV in tms-dev tms-prod; do
    cp -ux $ENV/* $SYSTEMD_INSTALL_DIR
done

# reload daemon for new/updated unit file
systemctl --user daemon-reload

for ENV in tms-dev tms-prod; do
    for UNIT in `ls $ENV`; do
        systemctl --user enable  $UNIT

        if [[ $(systemctl --user show $UNIT --property=UnitFileState | grep -q  '=enabled') != 0 ]]; then
            echo "failed to enable $UNIT"
        fi
    done
done