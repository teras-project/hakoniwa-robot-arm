#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash docker/attach.bash [humble|jazzy]
Default: jazzy. Open another interactive shell in the container started by run.bash.
Set CONTAINER_NAME if run.bash used a custom name.
The ROS underlay is sourced; Foundation/ROS project overlays are selected manually.
Exiting this shell leaves the original container running.
EOF
}

distro="${1:-jazzy}"
case "${distro}" in
  -h|--help) usage; exit 0 ;;
  humble|jazzy) ;;
  *) usage >&2; exit 2 ;;
esac
if [[ $# -gt 1 ]]; then usage >&2; exit 2; fi
command -v docker >/dev/null || { echo 'docker was not found on PATH' >&2; exit 127; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.bash
source "${script_dir}/env.bash"
name="${CONTAINER_NAME:-hakoniwa-arm-dev-${distro}}"
# docker exec skips ENTRYPOINT, so explicitly run the official ROS entrypoint.
exec docker exec -it --workdir "${HAKONIWA_CONTAINER_WORKDIR}" \
  "${name}" /ros_entrypoint.sh bash
