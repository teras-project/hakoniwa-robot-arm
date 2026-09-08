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
RECIPE_DIR="$PACK_ROOT/recipes/fr5"
SOURCE_YAML="$PACK_ROOT/sources/models/fr5/source.yaml"
FORGE_ROOT="$("$PYTHON_CMD" "$PACK_ROOT/tools/model_workspace.py" fr5)"
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

echo "=== FR5 Forge: Fetch Source ==="
echo "  - Pack root:   $PACK_ROOT"
echo "  - Source YAML: $SOURCE_YAML"
echo "  - Output dir:  $OUTPUT_DIR"

#
# Fetch FR5 source assets.
#
"$PYTHON_CMD" "$MBODY_ROOT/tools/fetch.py" \
    "$SOURCE_YAML" \
    --output-dir "$SOURCE_DIR"

cp -R "$SOURCE_DIR"/. "$BUILD_DIR"/

#
# Read entry URDF from fr5.yaml.
#
ENTRY_URDF_REL="$("$PYTHON_CMD" - <<'PY' "$SOURCE_YAML"
from pathlib import Path
import sys
import yaml

config = yaml.safe_load(
    Path(sys.argv[1]).read_text(encoding="utf-8")
)

entry_urdf = (
    config.get("forge", {})
    .get("entry_urdf", "")
)

print(entry_urdf)
PY
)"

if [ -z "$ENTRY_URDF_REL" ]; then
    echo "Error: forge.entry_urdf is not defined in $SOURCE_YAML"
    exit 1
fi

ENTRY_URDF="$BUILD_DIR/$ENTRY_URDF_REL"

if [ ! -f "$ENTRY_URDF" ]; then
    echo "Error: Entry URDF not found:"
    echo "  $ENTRY_URDF"
    exit 1
fi

echo
echo "FR5 source fetch complete."
echo "Entry URDF:"
echo "  $ENTRY_URDF"

PATCH_FILE="$PACK_ROOT/sources/models/fr5/patches/FR5WM.patch"

if [ ! -f "$PATCH_FILE" ]; then
    echo "Error: Patch file not found:"
    echo "  $PATCH_FILE"
    exit 1
fi

echo
echo "=== FR5 Forge: Apply Patch ==="
echo "  - Patch: $PATCH_FILE"

(
    cd "$BUILD_DIR"
    patch -p1 < "$PATCH_FILE"
)

echo "FR5 patch applied successfully."

#
# Convert DAE meshes to OBJ and rewrite URDF references.
#
OBJ_URDF="${ENTRY_URDF%.urdf}.obj.urdf"

echo
echo "=== FR5 Forge: Convert DAE to OBJ ==="
echo "  - Input URDF:  $ENTRY_URDF"
echo "  - Output URDF: $OBJ_URDF"

"$PYTHON_CMD" "$MBODY_ROOT/tools/urdf_dae2obj.py" \
    "$ENTRY_URDF" \
    --output "$OBJ_URDF"

if [ ! -f "$OBJ_URDF" ]; then
    echo "Error: OBJ-converted URDF not found:"
    echo "  $OBJ_URDF"
    exit 1
fi

echo "FR5 DAE to OBJ conversion complete."
echo "Converted URDF:"
echo "  $OBJ_URDF"

#
# Convert URDF to MJCF.
#
MJCF_FILE="$BUILD_DIR/FR5WM.xml"

echo
echo "=== FR5 Forge: Convert URDF to MJCF ==="
echo "  - Input URDF:  $OBJ_URDF"
echo "  - Output MJCF: $MJCF_FILE"

"$PYTHON_CMD" "$MBODY_ROOT/tools/urdf2mjcf.py" \
    "$OBJ_URDF" \
    --output "$MJCF_FILE"

if [ ! -f "$MJCF_FILE" ]; then
    echo "Error: MJCF file not found:"
    echo "  $MJCF_FILE"
    exit 1
fi

echo
echo "FR5 forge complete."
echo "MJCF:"
echo "  $MJCF_FILE"

ACTUATOR_CONFIG="$RECIPE_DIR/actuator.yaml"
RUNTIME_ACTUATOR_DIR="$RECIPE_DIR/config/actuator/joint"
RUNTIME_LIMIT_OVERRIDES="$RECIPE_DIR/config/actuator/runtime-limit-overrides.yaml"

if [ ! -f "$ACTUATOR_CONFIG" ]; then
    echo
    echo "=== FR5 Forge: Generate Actuator Config ==="
    echo "  - Input URDF:     $ENTRY_URDF"
    echo "  - Output Config:  $ACTUATOR_CONFIG"

    "$PYTHON_CMD" "$MBODY_ROOT/tools/urdf2actuator.py" \
        "$ENTRY_URDF" \
        --type position \
        --kp 100 \
        --dampratio 1.0 \
        --output "$ACTUATOR_CONFIG"

    if [ ! -f "$ACTUATOR_CONFIG" ]; then
        echo "Error: Actuator config not found:"
        echo "  $ACTUATOR_CONFIG"
        exit 1
    fi

    echo
    echo "FR5 actuator config generation complete."
    echo "Actuator config:"
    echo "  $ACTUATOR_CONFIG"
else
    echo
    echo "=== FR5 Forge: Actuator Config Already Exists ==="
    echo "  - Actuator config: $ACTUATOR_CONFIG"
fi

echo
echo "=== FR5 Forge: Synchronize Joint Limits ==="
LIMIT_SYNC_ARGS=(
    "$OBJ_URDF"
    --actuator-yaml "$ACTUATOR_CONFIG"
    --runtime-config-dir "$RUNTIME_ACTUATOR_DIR"
)
if [ -f "$RUNTIME_LIMIT_OVERRIDES" ]; then
    LIMIT_SYNC_ARGS+=(--runtime-limit-overrides "$RUNTIME_LIMIT_OVERRIDES")
fi
"$PYTHON_CMD" "$PACK_ROOT/tools/sync_arm_joint_limits.py" "${LIMIT_SYNC_ARGS[@]}"

ACTUATED_MJCF="$BUILD_DIR/FR5WM.actuated.xml"

echo
echo "=== FR5 Forge: Add Actuators to MJCF ==="
echo "  - Input MJCF:      $MJCF_FILE"
echo "  - Actuator config: $ACTUATOR_CONFIG"
echo "  - Output MJCF:     $ACTUATED_MJCF"

"$PYTHON_CMD" "$MBODY_ROOT/tools/mjcf_add_actuators.py" \
    "$MJCF_FILE" \
    "$ACTUATOR_CONFIG" \
    --output "$ACTUATED_MJCF"

if [ ! -f "$ACTUATED_MJCF" ]; then
    echo "Error: Actuated MJCF not found:"
    echo "  $ACTUATED_MJCF"
    exit 1
fi

echo
echo "FR5 actuator injection complete."
echo "Actuated MJCF:"
echo "  $ACTUATED_MJCF"

CONTACT_CONFIG="$SCRIPT_DIR/contact-excludes.yaml"
CONTACT_MJCF="$BUILD_DIR/FR5WM.contact.xml"

echo
echo "=== FR5 Forge: Add Contact Excludes ==="
echo "  - Input MJCF:     $ACTUATED_MJCF"
echo "  - Contact config: $CONTACT_CONFIG"
echo "  - Output MJCF:    $CONTACT_MJCF"

"$PYTHON_CMD" "$MBODY_ROOT/tools/mjcf_add_contact_excludes.py" \
    "$ACTUATED_MJCF" \
    "$CONTACT_CONFIG" \
    --output "$CONTACT_MJCF"

if [ ! -f "$CONTACT_MJCF" ]; then
    echo "Error: Contact-adjusted MJCF not found:"
    echo "  $CONTACT_MJCF"
    exit 1
fi

"$PYTHON_CMD" "$PACK_ROOT/tools/sync_arm_joint_limits.py" \
    "${LIMIT_SYNC_ARGS[@]}" \
    --validate-mjcf "$CONTACT_MJCF" \
    --check

echo
echo "FR5 contact excludes applied successfully."
echo "Contact-adjusted MJCF:"
echo "  $CONTACT_MJCF"

echo
echo "=== FR5 Forge: Install Generated Artifacts ==="
cp -R "$BUILD_DIR"/. "$STAGING_DIR"/
"$PYTHON_CMD" "$PACK_ROOT/tools/model_workspace.py" fr5 publish >/dev/null
echo "  - runtime MJCF: $OUTPUT_DIR/FR5WM.contact.xml"
