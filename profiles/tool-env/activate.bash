#!/usr/bin/env bash

# Shared tool environment for hakoniwa-robot-arm.
#
# Usage:
#   source /path/to/hakoniwa-robot-arm/profiles/tool-env/activate.bash
#
# This file resolves the Arm Pack, its checkout base, and the Composer without
# assuming that the checkout lives below $HOME. It deliberately does not set
# HAKONIWA_WORK_DIR or HAKONIWA_ROS2_WS: those values belong to a specific
# runtime configuration and must be supplied by the caller.

if [[ -n "${ZSH_VERSION:-}" ]]; then
  _tool_env_file="${(%):-%x}"
elif [[ -n "${BASH_VERSION:-}" ]]; then
  _tool_env_file="${BASH_SOURCE[0]}"
else
  echo "Source profiles/tool-env/activate.bash from Bash or zsh." >&2
  return 1 2>/dev/null || exit 1
fi

_tool_env_dir="$(cd -- "$(dirname -- "${_tool_env_file}")" && pwd -P)" || return 1

# docker/env.bash is the existing authoritative resolver for ARM_PACK and
# HAKONIWA_COMPOSER. It is intentionally sourceable from Host shells.
source "${_tool_env_dir}/../../docker/env.bash" || return 1

HAKOBASE_DIR="$(dirname -- "${ARM_PACK}")"
export HAKOBASE_DIR

unset _tool_env_file _tool_env_dir
