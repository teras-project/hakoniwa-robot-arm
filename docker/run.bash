#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash docker/run.bash [humble|jazzy] [docker run options...]
Default: jazzy. Open an interactive shell; exit stops/removes this container.
Use attach.bash from another terminal to open an additional shell.

Environment:
  HAKONIWA_COMPOSER Optional host Composer checkout (default: detected sibling)
  HAKONIWA_BUSINESS_PACK_ROOT Compatibility alias for HAKONIWA_COMPOSER
  HAKONIWA_DOCKER_WORK_DIR Optional container workdir
                           (default: /workspace/work-docker-<distro>)
  HAKONIWA_DOCKER_GUI auto|on|off (default: auto)
  HAKONIWA_DOCKER_DISPLAY Optional container DISPLAY override
  HAKONIWA_ROS2_TCP_CONFIG Optional host TCP config directory (from ros2_tcp.py config-root)
  IMAGE_NAME     Image repository (default: hakoniwa-arm-dev)
  CONTAINER_NAME Container name (default: hakoniwa-arm-dev-<distro>)
  DOCKER_NETWORK Network (default: host on Linux, bridge elsewhere)

Mount: Composer parent directory -> /workspace
Workdir: /workspace/<Composer directory name> (HAKONIWA_WORKSPACE_ROOT)
HAKONIWA_WORK_DIR: /workspace/work-docker-<distro>
Foundation runtime mmap: container-local tmpfs (not persisted on the Host)
ROS workspace: /workspace/ros2-work-<distro> (HAKONIWA_ROS2_WS)
No project build, source checkout, or Workspace enter is performed automatically.
EOF
}

distro="${1:-jazzy}"
case "${distro}" in
  -h|--help) usage; exit 0 ;;
  humble|jazzy) ;;
  *) usage >&2; exit 2 ;;
esac
if [[ $# -gt 0 ]]; then shift; fi
command -v docker >/dev/null || { echo 'docker was not found on PATH' >&2; exit 127; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.bash
source "${script_dir}/env.bash"
host_root="${HAKONIWA_COMPOSER_PARENT}"
run_options=(--rm -it)
if [[ "${ARM_PACK}" != "${host_root}"/* ]]; then
  if [[ "${HAKONIWA_CONTAINER_ARM_PACK}" == "${HAKONIWA_CONTAINER_COMPOSER}" ]]; then
    echo "Arm and Composer checkouts need distinct directory names for the container mount." >&2
    exit 1
  fi
  run_options+=(--volume "${ARM_PACK}:${HAKONIWA_CONTAINER_ARM_PACK}")
fi
if [[ -n "${HAKONIWA_ROS2_TCP_CONFIG:-}" ]]; then
  config_host="$(cd -- "${HAKONIWA_ROS2_TCP_CONFIG}" && pwd -P)"
  if [[ ! -f "${config_host}/ros/binding.json" ]]; then
    echo "Missing ${config_host}/ros/binding.json; configure the host ROS TCP recipe first." >&2
    exit 1
  fi
  # Independent mount: the host workdir may be outside the sibling directory.
  run_options+=(--volume "${config_host}:/ros2-tcp:ro"
    --env HAKONIWA_ROS2_TCP_CONFIG=/ros2-tcp
    --env HAKONIWA_ROS_BINDING=/ros2-tcp/ros/binding.json)
fi
host_os="$(uname -s)"
network="${DOCKER_NETWORK:-}"
if [[ -z "${network}" ]]; then
  if [[ "${host_os}" == Linux ]]; then network=host; else network=bridge; fi
fi

gui_mode="${HAKONIWA_DOCKER_GUI}"
case "${gui_mode}" in
  auto|on|off) ;;
  *) echo "HAKONIWA_DOCKER_GUI must be auto, on, or off: ${gui_mode}" >&2; exit 1 ;;
esac
gui_enabled=false
if [[ "${gui_mode}" == "on" ]]; then
  gui_enabled=true
elif [[ "${gui_mode}" == "auto" && -n "${DISPLAY:-}" ]]; then
  gui_enabled=true
fi
if [[ "${gui_enabled}" == true ]]; then
  if [[ -z "${DISPLAY:-}" && -z "${HAKONIWA_DOCKER_DISPLAY:-}" ]]; then
    echo "HAKONIWA_DOCKER_GUI=on requires DISPLAY." >&2
    exit 1
  fi
  container_display="${HAKONIWA_DOCKER_DISPLAY:-${DISPLAY:-}}"
  run_options+=(--env "DISPLAY=${container_display}")
  if [[ -d /tmp/.X11-unix ]]; then
    run_options+=(--volume /tmp/.X11-unix:/tmp/.X11-unix:rw)
  fi
  if [[ -d /dev/dri ]]; then
    run_options+=(--device /dev/dri)
  else
    run_options+=(--env LIBGL_ALWAYS_SOFTWARE=1)
  fi
else
  container_display="disabled"
  run_options+=(--env LIBGL_ALWAYS_SOFTWARE=1)
fi
name="${CONTAINER_NAME:-hakoniwa-arm-dev-${distro}}"
container_work_dir="${HAKONIWA_DOCKER_WORK_DIR:-/workspace/work-docker-${distro}}"
if [[ "${container_work_dir}" != /* ]]; then
  echo "HAKONIWA_DOCKER_WORK_DIR must be an absolute container path: ${container_work_dir}" >&2
  exit 1
fi
if [[ "${container_work_dir}" != "/" ]]; then
  container_work_dir="${container_work_dir%/}"
fi
mmap_dir="${container_work_dir%/}/foundation/runtime/mmap"
echo "Mount: ${host_root} -> /workspace"
echo "Container: ${name}; network: ${network}"
echo "GUI: ${gui_mode}; DISPLAY: ${container_display}"
echo "Workdir: ${container_work_dir}; Foundation mmap: tmpfs"
exec docker run "${run_options[@]}" --name "${name}" --network "${network}" \
  --volume "${host_root}:/workspace" \
  --tmpfs "${mmap_dir}:rw,nosuid,nodev,size=128m" \
  --workdir "${HAKONIWA_CONTAINER_WORKDIR}" \
  --env "HAKONIWA_COMPOSER=${HAKONIWA_CONTAINER_COMPOSER}" \
  --env "HAKONIWA_BUSINESS_PACK_ROOT=${HAKONIWA_CONTAINER_COMPOSER}" \
  --env "ARM_PACK=${HAKONIWA_CONTAINER_ARM_PACK}" \
  --env "HAKONIWA_WORK_DIR=${container_work_dir}" \
  --env "HAKONIWA_ROS2_WS=/workspace/ros2-work-${distro}" \
  "$@" "${IMAGE_NAME:-hakoniwa-arm-dev}:${distro}" bash
