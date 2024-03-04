#!/bin/bash
set -x  # turn on debugging
source tms_venv/bin/activate
exec "$@"