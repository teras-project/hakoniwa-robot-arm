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
SOURCE_YAML="$PACK_ROOT/sources/models/excavator/source.yaml"
FORGE_ROOT="$("$PYTHON_CMD" "$PACK_ROOT/tools/model_workspace.py" excavator)"
SOURCE_DIR="$FORGE_ROOT/source"
BUILD_DIR="$FORGE_ROOT/build"
OUTPUT_DIR="$FORGE_ROOT/install"
STAGING_DIR="$FORGE_ROOT/.install-next"
BUCKET_PROXY_PYTHON="${BUCKET_PROXY_PYTHON:-$FORGE_ROOT/tools-venv/bin/python}"

rm -rf "$SOURCE_DIR" "$BUILD_DIR" "$STAGING_DIR"
mkdir -p "$SOURCE_DIR" "$BUILD_DIR" "$STAGING_DIR"

if [ ! -f "$MBODY_ROOT/tools/fetch.py" ]; then
    echo "Error: hakoniwa-mbody-registry sibling checkout was not found:"
    echo "  $MBODY_ROOT"
    exit 1
fi
if [ ! -x "$BUCKET_PROXY_PYTHON" ]; then
    echo "Error: Recipe-owned bucket proxy environment was not found:"
    echo "  $BUCKET_PROXY_PYTHON"
    echo "Run: bash tools/install-excavator-bucket-proxy-tools.bash"
    exit 1
fi

echo "=== Excavator Forge: Fetch Pinned Source ==="
"$PYTHON_CMD" "$MBODY_ROOT/tools/fetch.py" "$SOURCE_YAML" --output-dir "$SOURCE_DIR"

UPSTREAM_PACKAGE="$SOURCE_DIR/ExcavatorCADFiles/URDF_MathScavator9000_flat/MathScavator9000_flat"
NORMALIZED_PACKAGE="$BUILD_DIR/model"
NORMALIZED_URDF="$NORMALIZED_PACKAGE/urdf/excavator.urdf"

echo
echo "=== Excavator Forge: Normalize URDF Meshes ==="
"$PYTHON_CMD" "$PACK_ROOT/tools/normalize_excavator_model.py" \
    "$UPSTREAM_PACKAGE" "$NORMALIZED_PACKAGE"
cp "$SOURCE_DIR/license.txt" "$BUILD_DIR/LICENSE"

echo
echo "=== Excavator Forge: Convert URDF to MJCF ==="
"$PYTHON_CMD" "$MBODY_ROOT/tools/urdf2mjcf.py" \
    "$NORMALIZED_URDF" \
    --package-root "MathScavator9000_flat.SLDASM=$NORMALIZED_PACKAGE" \
    --output "$BUILD_DIR/excavator.xml"

echo
echo "=== Excavator Forge: Add Position Actuators ==="
"$PYTHON_CMD" "$MBODY_ROOT/tools/mjcf_add_actuators.py" \
    "$BUILD_DIR/excavator.xml" "$SCRIPT_DIR/actuator.yaml" \
    --output "$BUILD_DIR/excavator.actuated.xml"

echo
echo "=== Excavator Forge: Configure Stable Integration ==="
"$PYTHON_CMD" "$PACK_ROOT/tools/configure_mjcf_options.py" \
    "$BUILD_DIR/excavator.actuated.xml" \
    --timestep 0.002 \
    --integrator implicitfast \
    --output "$BUILD_DIR/excavator.stabilized.xml"

echo
echo "=== Excavator Forge: Exclude Adjacent Joint Contacts ==="
"$PYTHON_CMD" "$MBODY_ROOT/tools/mjcf_add_contact_excludes.py" \
    "$BUILD_DIR/excavator.stabilized.xml" "$SCRIPT_DIR/contact-excludes.yaml" \
    --output "$BUILD_DIR/excavator.runtime.xml"

echo
echo "=== Excavator Forge: Add Six-wheel Differential Base ==="
"$PYTHON_CMD" "$PACK_ROOT/tools/configure_excavator_mobile_base.py" \
    "$BUILD_DIR/excavator.runtime.xml" \
    --output "$BUILD_DIR/excavator.mobile.xml"

echo
echo "=== Excavator Forge: Add Open Bucket Collision Shell ==="
"$BUCKET_PROXY_PYTHON" "$PACK_ROOT/tools/generate_excavator_bucket_collision.py" \
    "$BUILD_DIR/excavator.mobile.xml" \
    --config "$SCRIPT_DIR/bucket-collision.yaml" \
    --debug-output "$BUILD_DIR/excavator.bucket-proxy-debug.xml" \
    --output "$BUILD_DIR/excavator.bucket.xml"

echo
echo "=== Excavator Forge: Add HField Work Pit ==="
"$PYTHON_CMD" "$PACK_ROOT/tools/generate_excavator_hfield.py" \
    "$BUILD_DIR/excavator.bucket.xml" \
    --config "$SCRIPT_DIR/config/environment/terrain.json" \
    --heightmap-output "$BUILD_DIR/excavator-worksite-height.png" \
    --output "$BUILD_DIR/excavator.terrain.xml"

echo
echo "=== Excavator Forge: Add Simplified Granular Soil ==="
"$PYTHON_CMD" "$PACK_ROOT/tools/generate_excavator_soil.py" \
    "$BUILD_DIR/excavator.terrain.xml" \
    --config "$SCRIPT_DIR/config/environment/soil.json" \
    --output "$BUILD_DIR/excavator.soil.xml"

(
    cd "$BUILD_DIR"
    shasum -a 256 LICENSE excavator.runtime.xml excavator.mobile.xml \
        excavator.bucket.xml excavator.bucket-proxy-debug.xml \
        excavator.terrain.xml excavator.soil.xml \
        excavator-worksite-height.png \
        model/urdf/excavator.urdf \
        model/meshes/* > SHA256SUMS
)

cp -R "$BUILD_DIR"/. "$STAGING_DIR"/
"$PYTHON_CMD" "$PACK_ROOT/tools/model_workspace.py" excavator publish >/dev/null

echo "Excavator forge complete."
echo "  - runtime MJCF: $OUTPUT_DIR/excavator.runtime.xml"
echo "  - mobile MJCF:  $OUTPUT_DIR/excavator.mobile.xml"
echo "  - bucket MJCF:  $OUTPUT_DIR/excavator.bucket.xml"
echo "  - debug MJCF:   $OUTPUT_DIR/excavator.bucket-proxy-debug.xml"
echo "  - terrain MJCF: $OUTPUT_DIR/excavator.terrain.xml"
echo "  - soil MJCF:    $OUTPUT_DIR/excavator.soil.xml"
echo "  - source model: $OUTPUT_DIR/model"
echo "  - checksums:    $OUTPUT_DIR/SHA256SUMS"
