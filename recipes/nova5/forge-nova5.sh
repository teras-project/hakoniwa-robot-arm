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
SOURCE_YAML="$PACK_ROOT/sources/models/nova5/source.yaml"
FORGE_ROOT="$("$PYTHON_CMD" "$PACK_ROOT/tools/model_workspace.py" nova5)"
SOURCE_DIR="$FORGE_ROOT/source"
BUILD_DIR="$FORGE_ROOT/build"
OUTPUT_DIR="$FORGE_ROOT/install"
STAGING_DIR="$FORGE_ROOT/.install-next"

rm -rf "$SOURCE_DIR" "$BUILD_DIR" "$STAGING_DIR"
mkdir -p "$SOURCE_DIR" "$BUILD_DIR" "$STAGING_DIR"

if [ ! -f "$MBODY_ROOT/tools/fetch.py" ]; then
    echo "Error: hakoniwa-mbody-registry sibling checkout was not found:"
    echo "  $MBODY_ROOT"
    echo "Clone it next to this repository or set HAKONIWA_MBODY_REGISTRY_ROOT."
    exit 1
fi

echo "=== Nova5 Forge: Fetch Source ==="
"$PYTHON_CMD" "$MBODY_ROOT/tools/fetch.py" "$SOURCE_YAML" --output-dir "$SOURCE_DIR"
cp -R "$SOURCE_DIR"/. "$BUILD_DIR"/

ENTRY_XACRO="$BUILD_DIR/cra_description/urdf/nova5_robot.xacro"
NORMALIZED_URDF="$BUILD_DIR/cra_description/urdf/nova5_robot.urdf"
PACKAGE_ROOT="$BUILD_DIR/cra_description"
MJCF_FILE="$BUILD_DIR/nova5.xml"
ACTUATOR_CONFIG="$SCRIPT_DIR/actuator.yaml"
RUNTIME_ACTUATOR_DIR="$SCRIPT_DIR/config/actuator/joint"
RUNTIME_LIMIT_OVERRIDES="$SCRIPT_DIR/config/actuator/runtime-limit-overrides.yaml"
ACTUATED_MJCF="$BUILD_DIR/nova5.actuated.xml"
STABILIZED_MJCF="$BUILD_DIR/nova5.stabilized.xml"
CONTACT_CONFIG="$SCRIPT_DIR/contact-excludes.yaml"
CONTACT_MJCF="$BUILD_DIR/nova5.contact.xml"

echo
echo "=== Nova5 Forge: Normalize ROS Description ==="
"$PYTHON_CMD" "$PACK_ROOT/tools/normalize_nova5_urdf.py" \
    "$ENTRY_XACRO" --output "$NORMALIZED_URDF"

echo
echo "=== Nova5 Forge: Convert URDF to MJCF ==="
"$PYTHON_CMD" "$MBODY_ROOT/tools/urdf2mjcf.py" \
    "$NORMALIZED_URDF" \
    --package-root "cra_description=$PACKAGE_ROOT" \
    --output "$MJCF_FILE"

if [ ! -f "$ACTUATOR_CONFIG" ]; then
    echo
    echo "=== Nova5 Forge: Generate Actuator Config ==="
    "$PYTHON_CMD" "$MBODY_ROOT/tools/urdf2actuator.py" \
        "$NORMALIZED_URDF" \
        --type position \
        --kp 1000 \
        --dampratio 1.0 \
        --output "$ACTUATOR_CONFIG"
fi

echo
echo "=== Nova5 Forge: Synchronize Joint Limits ==="
LIMIT_SYNC_ARGS=(
    "$NORMALIZED_URDF"
    --actuator-yaml "$ACTUATOR_CONFIG"
    --runtime-config-dir "$RUNTIME_ACTUATOR_DIR"
)
if [ -f "$RUNTIME_LIMIT_OVERRIDES" ]; then
    LIMIT_SYNC_ARGS+=(--runtime-limit-overrides "$RUNTIME_LIMIT_OVERRIDES")
fi
"$PYTHON_CMD" "$PACK_ROOT/tools/sync_arm_joint_limits.py" "${LIMIT_SYNC_ARGS[@]}"

echo
echo "=== Nova5 Forge: Add Actuators ==="
"$PYTHON_CMD" "$MBODY_ROOT/tools/mjcf_add_actuators.py" \
    "$MJCF_FILE" "$ACTUATOR_CONFIG" --output "$ACTUATED_MJCF"

echo
echo "=== Nova5 Forge: Configure Simulation Options ==="
"$PYTHON_CMD" "$PACK_ROOT/tools/configure_mjcf_options.py" \
    "$ACTUATED_MJCF" \
    --timestep 0.002 \
    --integrator implicitfast \
    --output "$STABILIZED_MJCF"

echo
echo "=== Nova5 Forge: Add Contact Excludes ==="
"$PYTHON_CMD" "$MBODY_ROOT/tools/mjcf_add_contact_excludes.py" \
    "$STABILIZED_MJCF" "$CONTACT_CONFIG" --output "$CONTACT_MJCF"

"$PYTHON_CMD" "$PACK_ROOT/tools/sync_arm_joint_limits.py" \
    "${LIMIT_SYNC_ARGS[@]}" \
    --validate-mjcf "$CONTACT_MJCF" \
    --check

echo
echo "=== Nova5 Forge: Install Generated Artifacts ==="
cp -R "$BUILD_DIR/cra_description" "$STAGING_DIR/cra_description"
cp -R "$BUILD_DIR/nova5_moveit" "$STAGING_DIR/nova5_moveit"
cp "$BUILD_DIR/LICENSE" "$STAGING_DIR/LICENSE"
for generated_file in \
    nova5.xml \
    nova5.actuated.xml \
    nova5.stabilized.xml \
    nova5.contact.xml; do
    cp "$BUILD_DIR/$generated_file" "$STAGING_DIR/$generated_file"
done
"$PYTHON_CMD" "$PACK_ROOT/tools/model_workspace.py" nova5 publish >/dev/null

echo
echo "Nova5 forge complete."
echo "  - normalized URDF: $OUTPUT_DIR/cra_description/urdf/nova5_robot.urdf"
echo "  - runtime MJCF:    $OUTPUT_DIR/nova5.contact.xml"
