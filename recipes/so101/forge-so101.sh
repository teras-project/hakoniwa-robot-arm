#!/bin/bash

set -euo pipefail

if [ "$#" -ne 0 ]; then
    echo "Usage: $0"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_CMD="${PYTHON_CMD:-python3}"

exec "$PYTHON_CMD" "$SCRIPT_DIR/forge.py"
