#!/bin/bash
echo "tms entrypoint: activating venv"
source tms_venv/bin/activate
echo "tms entrypoint: executing command: $@"
exec "$@"