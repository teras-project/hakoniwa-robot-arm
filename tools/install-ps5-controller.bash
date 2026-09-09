#!/usr/bin/env bash
set -euo pipefail

if [[ "${HAKONIWA_WORKSPACE_ACTIVE:-}" != "1" ]]; then
  echo "Hakoniwa Workspace is not active." >&2
  echo "Run this installer from a shell opened by the Hakoniwa Composer workspace.py enter command." >&2
  exit 1
fi

if [[ -z "${HAKONIWA_WORKSPACE_ROOT:-}" || -z "${HAKONIWA_HOME:-}" || -z "${VIRTUAL_ENV:-}" ]]; then
  echo "Hakoniwa Workspace environment is incomplete." >&2
  exit 1
fi

WORK_DIR="${HAKONIWA_WORK_DIR:-${HAKONIWA_WORKSPACE_ROOT}/work}"
EXPECTED_HOME="${WORK_DIR}/foundation/install"
EXPECTED_VENV="${EXPECTED_HOME}/python"

if [[ "${HAKONIWA_HOME}" != "${EXPECTED_HOME}" ]]; then
  echo "Refusing to modify an unexpected HAKONIWA_HOME: ${HAKONIWA_HOME}" >&2
  echo "Expected: ${EXPECTED_HOME}" >&2
  exit 1
fi

if [[ "${VIRTUAL_ENV}" != "${EXPECTED_VENV}" ]]; then
  echo "Refusing to modify an unexpected Python environment: ${VIRTUAL_ENV}" >&2
  echo "Expected: ${EXPECTED_VENV}" >&2
  exit 1
fi

PYTHON="${EXPECTED_VENV}/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
  echo "Foundation Python not found: ${PYTHON}" >&2
  echo "Run the Recipe configure flow from Hakoniwa Composer first." >&2
  exit 1
fi

"${PYTHON}" -m pip install pygame==2.6.1
