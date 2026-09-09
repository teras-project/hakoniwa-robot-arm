#!/usr/bin/env bash

# Shared path configuration for docker/run.bash and docker/attach.bash.
# This file may also be sourced by a host shell to export the resolved paths.
if [[ -n "${ZSH_VERSION:-}" ]]; then
  # The file being sourced, including when source is called from a function.
  _arm_env_file="${(%):-%x}"
elif [[ -n "${BASH_VERSION:-}" ]]; then
  _arm_env_file="${BASH_SOURCE[0]}"
else
  echo "Source docker/env.bash from Bash or zsh." >&2
  return 1 2>/dev/null || exit 1
fi
_arm_docker_dir="$(cd -- "$(dirname -- "${_arm_env_file}")" && pwd -P)" || return 1
ARM_PACK="$(cd -- "${_arm_docker_dir}/.." && pwd -P)"
_arm_search_parent="${HOST_WORKDIR:-$(dirname -- "${ARM_PACK}")}"

HAKONIWA_COMPOSER="${HAKONIWA_COMPOSER:-${HAKONIWA_BUSINESS_PACK_ROOT:-}}"
if [[ -z "${HAKONIWA_COMPOSER}" ]]; then
  if [[ "${HAKONIWA_WORKSPACE_ACTIVE:-}" == 1 && -f "${HAKONIWA_WORKSPACE_ROOT:-}/tools/workspace.py" && -f "${HAKONIWA_WORKSPACE_ROOT:-}/tools/foundation.py" ]]; then
    HAKONIWA_COMPOSER="${HAKONIWA_WORKSPACE_ROOT}"
  elif [[ -d "${_arm_search_parent}/hakoniwa-business-pack" ]]; then
    # Preserve the conventional default when it exists.
    HAKONIWA_COMPOSER="${_arm_search_parent}/hakoniwa-business-pack"
  else
    # Discover by role, without assuming a repository name or executing code.
    for _arm_candidate in "${_arm_search_parent}"/*/; do
      if [[ -f "${_arm_candidate}tools/workspace.py" && -f "${_arm_candidate}tools/foundation.py" ]]; then
        if [[ -n "${HAKONIWA_COMPOSER}" ]]; then
          echo "Multiple Composer checkouts found; set HAKONIWA_COMPOSER explicitly." >&2
          unset HAKONIWA_COMPOSER
          return 1 2>/dev/null || exit 1
        fi
        HAKONIWA_COMPOSER="${_arm_candidate}"
      fi
    done
  fi
fi
if [[ ! -d "${HAKONIWA_COMPOSER}" ]]; then
  echo "Composer repository not found; set HAKONIWA_COMPOSER explicitly." >&2
  return 1 2>/dev/null || exit 1
fi
HAKONIWA_COMPOSER="$(cd -- "${HAKONIWA_COMPOSER}" && pwd -P)"
# Always publish the resolved Composer path through the legacy name too.  This
# prevents a stale, conflicting HAKONIWA_BUSINESS_PACK_ROOT from leaking into
# the container or into child tools.
HAKONIWA_BUSINESS_PACK_ROOT="${HAKONIWA_COMPOSER}"

# Docker policy defaults. Callers may set these before sourcing this file.
HAKONIWA_DOCKER_GUI="${HAKONIWA_DOCKER_GUI:-auto}"

# The whole sibling directory is mounted so Arm Pack and its dependencies
# retain their existing relative placement.  The container path is derived
# from the selected checkout name rather than hard-coded to business-pack.
HAKONIWA_COMPOSER_NAME="$(basename -- "${HAKONIWA_COMPOSER}")"
HAKONIWA_COMPOSER_PARENT="$(dirname -- "${HAKONIWA_COMPOSER}")"
HAKONIWA_CONTAINER_COMPOSER="/workspace/${HAKONIWA_COMPOSER_NAME}"
HAKONIWA_CONTAINER_WORKDIR="${HAKONIWA_CONTAINER_COMPOSER}"
case "${ARM_PACK}" in
  "${HAKONIWA_COMPOSER_PARENT}"/*)
    HAKONIWA_CONTAINER_ARM_PACK="/workspace/${ARM_PACK#"${HAKONIWA_COMPOSER_PARENT}"/}"
    ;;
  *) HAKONIWA_CONTAINER_ARM_PACK="/workspace/$(basename -- "${ARM_PACK}")" ;;
esac
export ARM_PACK HAKONIWA_COMPOSER HAKONIWA_BUSINESS_PACK_ROOT HAKONIWA_DOCKER_GUI

unset _arm_env_file _arm_docker_dir _arm_search_parent _arm_candidate
