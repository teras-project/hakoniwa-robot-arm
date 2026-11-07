#!/usr/bin/env python3
"""Generate a manually calibrated excavator bucket collision proxy."""

from __future__ import annotations

import argparse
import copy
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml


PART_NAMES = ("floor", "back", "side_left", "side_right", "cutting_edge")
FORBIDDEN_PART_NAMES = {"front", "ceiling"}
TOP_LEVEL_KEYS = {"version", "calibration", "frame", "defaults", "parts", "debug"}
FRAME_KEYS = {"parent", "description", "origin_in_parent_m", "rpy_deg"}
DEFAULT_KEYS = {
    "contype", "conaffinity", "condim", "friction", "density", "group"
}
PART_KEYS = {
    "enabled", "type", "description", "center_m", "dimensions_m", "rpy_deg", "rgba"
}
DEBUG_KEYS = {
    "enabled", "visual_mesh_alpha", "show_proxy_frame",
    "show_part_labels", "show_collision_parts", "show_parent_frame",
}
CALIBRATION_KEYS = {"status", "note"}


class BucketCollisionError(ValueError):
    pass


def require_mapping(value, path: str) -> dict:
    if not isinstance(value, dict):
        raise BucketCollisionError(f"{path} must be a mapping")
    return value


def reject_unknown(mapping: dict, allowed: set[str], path: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise BucketCollisionError(f"{path} has unknown keys: {', '.join(unknown)}")


def finite_number(value, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BucketCollisionError(f"{path} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise BucketCollisionError(f"{path} must be a finite number")
    return result


def vector(value, length: int, path: str) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise BucketCollisionError(f"{path} must contain {length} numbers")
    return tuple(finite_number(item, f"{path}[{index}]") for index, item in enumerate(value))


def boolean(value, path: str) -> bool:
    if not isinstance(value, bool):
        raise BucketCollisionError(f"{path} must be true or false")
    return value


def load_bucket_collision(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    root = require_mapping(payload, "$")
    reject_unknown(root, TOP_LEVEL_KEYS, "$")
    if root.get("version") != 1:
        raise BucketCollisionError("$.version must be 1")

    calibration = require_mapping(root.get("calibration"), "$.calibration")
    reject_unknown(calibration, CALIBRATION_KEYS, "$.calibration")
    calibration_status = calibration.get("status")
    if calibration_status not in {"unverified", "accepted"}:
        raise BucketCollisionError(
            "$.calibration.status must be unverified or accepted"
        )
    calibration_note = calibration.get("note", "")
    if not isinstance(calibration_note, str):
        raise BucketCollisionError("$.calibration.note must be a string")

    frame = require_mapping(root.get("frame"), "$.frame")
    reject_unknown(frame, FRAME_KEYS, "$.frame")
    parent = frame.get("parent")
    if not isinstance(parent, str) or not parent:
        raise BucketCollisionError("$.frame.parent must be a non-empty string")
    frame_description = frame.get("description")
    if not isinstance(frame_description, str) or not frame_description.strip():
        raise BucketCollisionError("$.frame.description must be a non-empty string")
    normalized_frame = {
        "parent": parent,
        "description": frame_description,
        "origin_in_parent_m": vector(
            frame.get("origin_in_parent_m"), 3, "$.frame.origin_in_parent_m"
        ),
        "rpy_deg": vector(frame.get("rpy_deg"), 3, "$.frame.rpy_deg"),
    }

    defaults = require_mapping(root.get("defaults"), "$.defaults")
    reject_unknown(defaults, DEFAULT_KEYS, "$.defaults")
    normalized_defaults = {
        "contype": int(finite_number(defaults.get("contype"), "$.defaults.contype")),
        "conaffinity": int(finite_number(defaults.get("conaffinity"), "$.defaults.conaffinity")),
        "condim": int(finite_number(defaults.get("condim"), "$.defaults.condim")),
        "friction": vector(defaults.get("friction"), 3, "$.defaults.friction"),
        "density": finite_number(defaults.get("density"), "$.defaults.density"),
        "group": int(finite_number(defaults.get("group"), "$.defaults.group")),
    }
    if normalized_defaults["density"] != 0.0:
        raise BucketCollisionError("$.defaults.density must be 0")
    if any(item < 0.0 for item in normalized_defaults["friction"]):
        raise BucketCollisionError("$.defaults.friction values must be non-negative")

    parts = require_mapping(root.get("parts"), "$.parts")
    forbidden = sorted(set(parts) & FORBIDDEN_PART_NAMES)
    if forbidden:
        raise BucketCollisionError(
            f"$.parts must not define a front or ceiling: {', '.join(forbidden)}"
        )
    missing = sorted(set(PART_NAMES) - set(parts))
    extra = sorted(set(parts) - set(PART_NAMES))
    if missing or extra:
        raise BucketCollisionError(
            f"$.parts must contain exactly {', '.join(PART_NAMES)}; "
            f"missing={missing}, extra={extra}"
        )
    normalized_parts = {}
    for name in PART_NAMES:
        part_path = f"$.parts.{name}"
        part = require_mapping(parts[name], part_path)
        reject_unknown(part, PART_KEYS, part_path)
        if part.get("type") != "box":
            raise BucketCollisionError(
                f"{part_path}.type must be box in schema version 1"
            )
        description = part.get("description")
        if not isinstance(description, str) or not description.strip():
            raise BucketCollisionError(f"{part_path}.description must be a non-empty string")
        dimensions = vector(part.get("dimensions_m"), 3, f"{part_path}.dimensions_m")
        if any(item <= 0.0 for item in dimensions):
            raise BucketCollisionError(f"{part_path}.dimensions_m must be positive")
        rgba = vector(part.get("rgba"), 4, f"{part_path}.rgba")
        if any(item < 0.0 or item > 1.0 for item in rgba):
            raise BucketCollisionError(f"{part_path}.rgba must be within [0, 1]")
        normalized_parts[name] = {
            "enabled": boolean(part.get("enabled"), f"{part_path}.enabled"),
            "type": "box",
            "description": description,
            "center_m": vector(part.get("center_m"), 3, f"{part_path}.center_m"),
            "dimensions_m": dimensions,
            "rpy_deg": vector(part.get("rpy_deg"), 3, f"{part_path}.rpy_deg"),
            "rgba": rgba,
        }

    debug = require_mapping(root.get("debug"), "$.debug")
    reject_unknown(debug, DEBUG_KEYS, "$.debug")
    alpha = finite_number(debug.get("visual_mesh_alpha"), "$.debug.visual_mesh_alpha")
    if not 0.0 <= alpha <= 1.0:
        raise BucketCollisionError("$.debug.visual_mesh_alpha must be within [0, 1]")
    normalized_debug = {
        "enabled": boolean(debug.get("enabled"), "$.debug.enabled"),
        "visual_mesh_alpha": alpha,
        "show_proxy_frame": boolean(
            debug.get("show_proxy_frame"), "$.debug.show_proxy_frame"
        ),
        "show_part_labels": boolean(
            debug.get("show_part_labels"), "$.debug.show_part_labels"
        ),
        "show_collision_parts": boolean(
            debug.get("show_collision_parts"), "$.debug.show_collision_parts"
        ),
        "show_parent_frame": boolean(
            debug.get("show_parent_frame"), "$.debug.show_parent_frame"
        ),
    }
    return {
        "version": 1,
        "calibration": {"status": calibration_status, "note": calibration_note},
        "frame": normalized_frame,
        "defaults": normalized_defaults,
        "parts": normalized_parts,
        "debug": normalized_debug,
    }


def matrix_multiply(left, right):
    return tuple(
        tuple(sum(left[row][k] * right[k][column] for k in range(3)) for column in range(3))
        for row in range(3)
    )


def matrix_vector(matrix, value):
    return tuple(sum(matrix[row][column] * value[column] for column in range(3)) for row in range(3))


def rpy_deg_matrix(rpy_deg):
    roll, pitch, yaw = (math.radians(value) for value in rpy_deg)
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rx = ((1, 0, 0), (0, cr, -sr), (0, sr, cr))
    ry = ((cp, 0, sp), (0, 1, 0), (-sp, 0, cp))
    rz = ((cy, -sy, 0), (sy, cy, 0), (0, 0, 1))
    return matrix_multiply(matrix_multiply(rz, ry), rx)


def matrix_quaternion_wxyz(matrix):
    trace = matrix[0][0] + matrix[1][1] + matrix[2][2]
    if trace > 0.0:
        scale = math.sqrt(trace + 1.0) * 2.0
        w = 0.25 * scale
        x = (matrix[2][1] - matrix[1][2]) / scale
        y = (matrix[0][2] - matrix[2][0]) / scale
        z = (matrix[1][0] - matrix[0][1]) / scale
    elif matrix[0][0] > matrix[1][1] and matrix[0][0] > matrix[2][2]:
        scale = math.sqrt(1.0 + matrix[0][0] - matrix[1][1] - matrix[2][2]) * 2.0
        w = (matrix[2][1] - matrix[1][2]) / scale
        x = 0.25 * scale
        y = (matrix[0][1] + matrix[1][0]) / scale
        z = (matrix[0][2] + matrix[2][0]) / scale
    elif matrix[1][1] > matrix[2][2]:
        scale = math.sqrt(1.0 + matrix[1][1] - matrix[0][0] - matrix[2][2]) * 2.0
        w = (matrix[0][2] - matrix[2][0]) / scale
        x = (matrix[0][1] + matrix[1][0]) / scale
        y = 0.25 * scale
        z = (matrix[1][2] + matrix[2][1]) / scale
    else:
        scale = math.sqrt(1.0 + matrix[2][2] - matrix[0][0] - matrix[1][1]) * 2.0
        w = (matrix[1][0] - matrix[0][1]) / scale
        x = (matrix[0][2] + matrix[2][0]) / scale
        y = (matrix[1][2] + matrix[2][1]) / scale
        z = 0.25 * scale
    quaternion = (w, x, y, z)
    length = math.sqrt(sum(value * value for value in quaternion))
    quaternion = tuple(value / length for value in quaternion)
    return tuple(-value for value in quaternion) if quaternion[0] < 0.0 else quaternion


def transform_part(config: dict, part: dict) -> tuple[tuple[float, ...], tuple[float, ...]]:
    frame_rotation = rpy_deg_matrix(config["frame"]["rpy_deg"])
    part_rotation = rpy_deg_matrix(part["rpy_deg"])
    rotated_center = matrix_vector(frame_rotation, part["center_m"])
    position = tuple(
        config["frame"]["origin_in_parent_m"][index] + rotated_center[index]
        for index in range(3)
    )
    rotation = matrix_multiply(frame_rotation, part_rotation)
    return position, matrix_quaternion_wxyz(rotation)


def values(items) -> str:
    return " ".join(f"{float(item):.12g}" for item in items)


def find_parent(root: ET.Element, parent_name: str) -> ET.Element:
    parent = root.find(f".//body[@name='{parent_name}']")
    if parent is None:
        raise BucketCollisionError(f"parent body not found in MJCF: {parent_name}")
    return parent


def remove_old_proxy(parent: ET.Element) -> None:
    for geom in list(parent.findall("geom")):
        name = geom.get("name") or ""
        if name.startswith("bucket_collision_") or name.startswith("bucket_proxy_"):
            parent.remove(geom)


def add_proxy_geoms(parent: ET.Element, config: dict) -> None:
    defaults = config["defaults"]
    for name in PART_NAMES:
        part = config["parts"][name]
        if not part["enabled"]:
            continue
        position, quaternion = transform_part(config, part)
        runtime_rgba = list(part["rgba"])
        runtime_rgba[3] = 0.0
        ET.SubElement(
            parent,
            "geom",
            {
                "name": f"bucket_proxy_{name}",
                "type": "box",
                "pos": values(position),
                "size": values(value / 2.0 for value in part["dimensions_m"]),
                "quat": values(quaternion),
                "contype": str(defaults["contype"]),
                "conaffinity": str(defaults["conaffinity"]),
                "condim": str(defaults["condim"]),
                "friction": values(defaults["friction"]),
                "density": "0",
                "group": str(defaults["group"]),
                # Runtime collision remains physical but is visually hidden.
                # The separate debug model restores the calibrated part color.
                "rgba": values(runtime_rgba),
            },
        )


def disable_bucket_mesh_collision(parent: ET.Element) -> None:
    for geom in parent.findall("geom[@type='mesh']"):
        geom.set("contype", "0")
        geom.set("conaffinity", "0")


def add_debug_frame(parent: ET.Element, config: dict) -> None:
    if not config["debug"]["show_proxy_frame"]:
        return
    origin = config["frame"]["origin_in_parent_m"]
    rotation = rpy_deg_matrix(config["frame"]["rpy_deg"])
    ET.SubElement(parent, "geom", {
        "name": "bucket_proxy_frame_origin", "type": "sphere",
        "pos": values(origin), "size": "0.035", "rgba": "1 1 1 1",
        "contype": "0", "conaffinity": "0", "density": "0", "group": "0",
    })
    for index, (axis_name, color) in enumerate(
        (("x", "1 0 0 1"), ("y", "0 1 0 1"), ("z", "0 0.4 1 1"))
    ):
        direction = tuple(rotation[row][index] for row in range(3))
        endpoint = tuple(origin[row] + 0.30 * direction[row] for row in range(3))
        ET.SubElement(parent, "geom", {
            "name": f"bucket_proxy_frame_axis_{axis_name}", "type": "capsule",
            "fromto": values((*origin, *endpoint)), "size": "0.012",
            "rgba": color, "contype": "0", "conaffinity": "0",
            "density": "0", "group": "0",
        })


def add_parent_frame(parent: ET.Element, config: dict) -> None:
    if not config["debug"]["show_parent_frame"]:
        return
    origin = (0.0, 0.0, 0.0)
    ET.SubElement(parent, "geom", {
        "name": "stick_bucket_link_frame_origin", "type": "sphere",
        "pos": "0 0 0", "size": "0.05", "rgba": "1 0.2 1 1",
        "contype": "0", "conaffinity": "0", "density": "0", "group": "0",
    })
    for axis_name, endpoint, color in (
        ("x", (0.45, 0.0, 0.0), "1 0 0 0.75"),
        ("y", (0.0, 0.45, 0.0), "0 1 0 0.75"),
        ("z", (0.0, 0.0, 0.45), "0 0.4 1 0.75"),
    ):
        ET.SubElement(parent, "geom", {
            "name": f"stick_bucket_link_frame_axis_{axis_name}",
            "type": "capsule", "fromto": values((*origin, *endpoint)),
            "size": "0.018", "rgba": color, "contype": "0",
            "conaffinity": "0", "density": "0", "group": "0",
        })


def make_debug_tree(tree: ET.ElementTree, config: dict) -> ET.ElementTree:
    debug_tree = copy.deepcopy(tree)
    root = debug_tree.getroot()
    parent = find_parent(root, config["frame"]["parent"])
    alpha = config["debug"]["visual_mesh_alpha"]
    for geom in parent.findall("geom[@type='mesh']"):
        rgba = [float(value) for value in geom.get("rgba", "1 1 1 1").split()]
        if len(rgba) == 4 and geom.get("group") == "1":
            rgba[3] = alpha
            geom.set("rgba", values(rgba))
    for name in PART_NAMES:
        geom = parent.find(f"geom[@name='bucket_proxy_{name}']")
        if geom is None:
            continue
        rgba = list(config["parts"][name]["rgba"])
        if not config["debug"]["show_collision_parts"]:
            rgba[3] = 0.0
        geom.set("rgba", values(rgba))
    add_parent_frame(parent, config)
    add_debug_frame(parent, config)
    return debug_tree


def write_tree(tree: ET.ElementTree, output: Path) -> None:
    ET.indent(tree, space="  ")
    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output, encoding="utf-8", xml_declaration=True)


def generate(input_path: Path, config_path: Path, output_path: Path, debug_output: Path | None) -> dict:
    config = load_bucket_collision(config_path)
    tree = ET.parse(input_path)
    parent = find_parent(tree.getroot(), config["frame"]["parent"])
    remove_old_proxy(parent)
    disable_bucket_mesh_collision(parent)
    add_proxy_geoms(parent, config)
    write_tree(tree, output_path)
    if debug_output is not None and config["debug"]["enabled"]:
        write_tree(make_debug_tree(tree, config), debug_output)
    return config


def launch_viewer(model_path: Path) -> None:
    import mujoco
    import mujoco.viewer

    def loader():
        model = mujoco.MjModel.from_xml_path(str(model_path))
        data = mujoco.MjData(model)
        key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "excavator_home")
        if key >= 0:
            mujoco.mj_resetDataKeyframe(model, data, key)
        else:
            mujoco.mj_forward(model, data)
        return model, data, str(model_path)

    print(
        "Viewer reload is enabled. Regenerate from another terminal, then use "
        "the standard Reload control in this Viewer.",
        flush=True,
    )
    mujoco.viewer.launch(loader=loader)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--debug-output", type=Path)
    parser.add_argument("--viewer", action="store_true")
    args = parser.parse_args()
    try:
        config = generate(args.input, args.config, args.output, args.debug_output)
        if args.viewer:
            if args.debug_output is None:
                raise BucketCollisionError("--viewer requires --debug-output")
            launch_viewer(args.debug_output)
    except (BucketCollisionError, OSError, ET.ParseError, yaml.YAMLError) as error:
        parser.error(str(error))
    print(f"Generated bucket proxy: {args.output}")
    print(f"Calibration status: {config['calibration']['status']}")
    if args.debug_output is not None:
        print(f"Generated debug model: {args.debug_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
