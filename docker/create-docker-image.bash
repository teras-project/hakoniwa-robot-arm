#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash docker/create-docker-image.bash [humble|jazzy|all] [docker build options...]
Default: all. Images: hakoniwa-arm-dev:humble and hakoniwa-arm-dev:jazzy.
Set IMAGE_NAME to change the image repository name.
Examples:
  bash docker/create-docker-image.bash jazzy
  bash docker/create-docker-image.bash all --no-cache
  bash docker/create-docker-image.bash humble --platform linux/arm64
EOF
}

selection="${1:-all}"
case "${selection}" in
  -h|--help) usage; exit 0 ;;
  humble|jazzy|all) ;;
  *) usage >&2; exit 2 ;;
esac
if [[ $# -gt 0 ]]; then shift; fi
command -v docker >/dev/null || { echo 'docker was not found on PATH' >&2; exit 127; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
distros=("${selection}")
if [[ "${selection}" == all ]]; then distros=(humble jazzy); fi
for distro in "${distros[@]}"; do
  docker build "$@" --file "${script_dir}/Dockerfile.${distro}" \
    --tag "${IMAGE_NAME:-hakoniwa-arm-dev}:${distro}" "${script_dir}"
done
