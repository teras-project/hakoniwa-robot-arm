#!/usr/bin/env bash

# Open the initial host-only Hakoniwa Workspace. This bootstrap profile is
# usable immediately after clone; configure later writes a work-owned
# activate-host-hako.bash for reopening the same configuration.

if [[ -n "${ZSH_VERSION:-}" ]]; then
  _host_hako_file="${(%):-%x}"
elif [[ -n "${BASH_VERSION:-}" ]]; then
  _host_hako_file="${BASH_SOURCE[0]}"
else
  echo "Source profiles/tool-env/enter-host-hako.bash from Bash or zsh." >&2
  return 1 2>/dev/null || exit 1
fi

_host_hako_dir="$(cd -- "$(dirname -- "${_host_hako_file}")" && pwd -P)" || return 1
source "${_host_hako_dir}/activate.bash" || return 1

export HAKONIWA_WORK_DIR="${HAKONIWA_WORK_DIR:-${HAKOBASE_DIR}/work-host}"
export HAKONIWA_ROS2_WS="${HAKONIWA_ROS2_WS:-${HAKONIWA_WORK_DIR}/ros2}"
# host-only ROS processes connect to the Host-local TCP bridge.
export HAKONIWA_ROS2_TCP_HOST="${HAKONIWA_ROS2_TCP_HOST:-127.0.0.1}"
export HAKO_TERMINAL_ROLE=host-hako

if [[ "${HAKONIWA_WORKSPACE_ACTIVE:-}" == "1" ]]; then
  echo "host-hako is already active; use this bootstrap profile from a normal Host shell." >&2
  return 1
fi

python3.12 "$HAKONIWA_COMPOSER/tools/workspace.py" enter --workdir "$HAKONIWA_WORK_DIR"

unset _host_hako_file _host_hako_dir
