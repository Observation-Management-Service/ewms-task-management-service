#!/bin/bash
set -euo pipefail
echo "tms entrypoint: activating venv"
source /app/venv/bin/activate
echo "tms entrypoint: executing command: $@"
exec "$@"
