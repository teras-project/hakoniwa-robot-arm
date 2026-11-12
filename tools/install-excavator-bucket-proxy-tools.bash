#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_CMD="${PYTHON_CMD:-python3}"

exec "$PYTHON_CMD" "$SCRIPT_DIR/install_excavator_bucket_proxy_tools.py"
