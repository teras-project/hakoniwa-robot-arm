#!/bin/bash

set -euo pipefail

if [ "$#" -ne 0 ]; then
    echo "Usage: $0"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MBODY_ROOT="${HAKONIWA_MBODY_REGISTRY_ROOT:-$PACK_ROOT/../hakoniwa-mbody-registry}"
PYTHON_CMD="${PYTHON_CMD:-python3}"
SOURCE_YAML="$PACK_ROOT/sources/models/so101/source.yaml"
RUNTIME_ACTUATOR_DIR="$SCRIPT_DIR/config/actuator/joint"
RUNTIME_LIMIT_OVERRIDES="$SCRIPT_DIR/config/actuator/runtime-limit-overrides.yaml"
FORGE_ROOT="$("$PYTHON_CMD" "$PACK_ROOT/tools/model_workspace.py" so101)"
SOURCE_DIR="$FORGE_ROOT/source"
BUILD_DIR="$FORGE_ROOT/build"
OUTPUT_DIR="$FORGE_ROOT/install"
STAGING_DIR="$FORGE_ROOT/.install-next"

rm -rf "$SOURCE_DIR" "$BUILD_DIR" "$STAGING_DIR"
mkdir -p "$SOURCE_DIR" "$BUILD_DIR" "$STAGING_DIR"

if [ ! -f "$MBODY_ROOT/tools/fetch.py" ]; then
    echo "Error: hakoniwa-mbody-registry sibling checkout was not found:"
    echo "  $MBODY_ROOT"
    exit 1
fi

echo "=== SO-101 Forge: Fetch Pinned Source ==="
"$PYTHON_CMD" "$MBODY_ROOT/tools/fetch.py" "$SOURCE_YAML" --output-dir "$SOURCE_DIR"

UPSTREAM="$SOURCE_DIR/Simulation/SO101"
mkdir -p "$BUILD_DIR/assets"
cp "$UPSTREAM"/assets/*.stl "$BUILD_DIR/assets/"
cp "$SOURCE_DIR/LICENSE" "$BUILD_DIR/LICENSE"
cp "$UPSTREAM/so101_new_calib.xml" "$BUILD_DIR/so101.xml"

"$PYTHON_CMD" "$PACK_ROOT/tools/configure_mjcf_options.py" \
    "$BUILD_DIR/so101.xml" \
    --timestep 0.002 \
    --integrator implicitfast \
    --output "$BUILD_DIR/so101.xml"

echo
echo "=== SO-101 Forge: Synchronize Joint Limits ==="
LIMIT_SYNC_ARGS=(
    "$UPSTREAM/so101_new_calib.urdf"
    --runtime-config-dir "$RUNTIME_ACTUATOR_DIR"
    --validate-mjcf "$BUILD_DIR/so101.xml"
)
if [ -f "$RUNTIME_LIMIT_OVERRIDES" ]; then
    LIMIT_SYNC_ARGS+=(--runtime-limit-overrides "$RUNTIME_LIMIT_OVERRIDES")
fi
"$PYTHON_CMD" "$PACK_ROOT/tools/sync_arm_joint_limits.py" "${LIMIT_SYNC_ARGS[@]}"

(
    cd "$BUILD_DIR"
    shasum -a 256 LICENSE so101.xml assets/*.stl > SHA256SUMS
)

cp -R "$BUILD_DIR"/. "$STAGING_DIR"/
"$PYTHON_CMD" "$PACK_ROOT/tools/model_workspace.py" so101 publish >/dev/null

echo "SO-101 forge complete."
echo "  - runtime MJCF: $OUTPUT_DIR/so101.xml"
echo "  - mesh assets:  $OUTPUT_DIR/assets"
echo "  - checksums:     $OUTPUT_DIR/SHA256SUMS"
