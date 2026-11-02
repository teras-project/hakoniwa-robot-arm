#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FORGE_ROOT="$(python3.12 "${PACK_ROOT}/tools/model_workspace.py" excavator)"
TOOLS_VENV="${FORGE_ROOT}/tools-venv"
TOOLS_PYTHON="${TOOLS_VENV}/bin/python"
REQUIREMENTS="${PACK_ROOT}/recipes/excavator/bucket-proxy-requirements.txt"

if [[ ! -x "${TOOLS_PYTHON}" ]]; then
  python3.12 -m venv "${TOOLS_VENV}"
fi

"${TOOLS_PYTHON}" -m pip install --requirement "${REQUIREMENTS}"
"${TOOLS_PYTHON}" -c 'import mujoco, mujoco.viewer, numpy, trimesh, yaml; print("Excavator bucket-proxy tools are ready.")'
