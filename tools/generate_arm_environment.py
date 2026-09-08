#!/usr/bin/env python3
"""Materialize a static MuJoCo workspace around an existing robot model."""

from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path


def vector(value, length: int, field: str) -> str:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"{field} must contain {length} numbers")
    return " ".join(str(float(item)) for item in value)


def rpy_degrees_to_quaternion(value, field: str) -> str:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{field} must contain roll, pitch, yaw in degrees")
    roll, pitch, yaw = (math.radians(float(item)) for item in value)
    cr, sr = math.cos(roll / 2.0), math.sin(roll / 2.0)
    cp, sp = math.cos(pitch / 2.0), math.sin(pitch / 2.0)
    cy, sy = math.cos(yaw / 2.0), math.sin(yaw / 2.0)
    quaternion = (
        cr * cp * cy + sr * sp * sy,
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy,
    )
    norm = math.sqrt(sum(component * component for component in quaternion))
    return " ".join(str(component / norm) for component in quaternion)


def apply_robot_visual(root: ET.Element, config: dict) -> None:
    """Apply optional Recipe-owned colors without changing robot dynamics."""
    robot_visual = config.get("robot_visual")
    if robot_visual is None:
        return

    mesh_rgba = robot_visual.get("mesh_rgba", {})
    if not isinstance(mesh_rgba, dict):
        raise ValueError("robot_visual.mesh_rgba must be an object")

    matched = {mesh_name: 0 for mesh_name in mesh_rgba}
    for geom in root.findall(".//geom"):
        mesh_name = geom.get("mesh")
        if mesh_name in mesh_rgba:
            geom.set(
                "rgba",
                vector(
                    mesh_rgba[mesh_name],
                    4,
                    f"robot_visual.mesh_rgba.{mesh_name}",
                ),
            )
            matched[mesh_name] += 1

    missing = [mesh_name for mesh_name, count in matched.items() if count == 0]
    if missing:
        raise ValueError(
            "robot_visual.mesh_rgba references unknown meshes: " + ", ".join(missing)
        )


def apply_robot_collision_pads(root: ET.Element, config: dict) -> None:
    """Attach Recipe-owned primitive contact pads to named robot bodies."""
    pads = config.get("robot_collision_pads", [])
    existing_names = {
        geom.get("name") for geom in root.findall(".//geom") if geom.get("name")
    }
    bodies = {
        body.get("name"): body
        for body in root.findall(".//body")
        if body.get("name")
    }

    for pad in pads:
        name = pad["name"]
        if name in existing_names:
            raise ValueError(f"duplicate robot collision geom name: {name}")
        existing_names.add(name)
        body_name = pad["body"]
        body = bodies.get(body_name)
        if body is None:
            raise ValueError(f"robot collision pad references unknown body: {body_name}")
        if pad.get("type") != "box":
            raise ValueError(f"unsupported robot collision pad type: {pad.get('type')}")

        replaced_mesh = pad.get("replaces_collision_mesh")
        if replaced_mesh is not None:
            matching_collision_geoms = [
                geom
                for geom in body.findall("geom")
                if geom.get("class") == "collision"
                and geom.get("mesh") == replaced_mesh
            ]
            if not matching_collision_geoms:
                raise ValueError(
                    f"robot collision pad references unknown collision mesh: "
                    f"{replaced_mesh} on body {body_name}"
                )
            for collision_geom in matching_collision_geoms:
                collision_geom.set("contype", "0")
                collision_geom.set("conaffinity", "0")

        geom = ET.Element(
            "geom",
            {
                "name": name,
                "type": "box",
                "pos": vector(pad["pos_local_m"], 3, f"{name}.pos_local_m"),
                "quat": rpy_degrees_to_quaternion(
                    pad["rpy_deg"], f"{name}.rpy_deg"
                ),
                "size": vector(pad["half_size_m"], 3, f"{name}.half_size_m"),
                "density": "0",
                "rgba": vector(pad["rgba"], 4, f"{name}.rgba"),
                "friction": vector(pad["friction"], 3, f"{name}.friction"),
                "condim": "4",
                "contype": "1",
                "conaffinity": "1",
                "group": "1" if pad.get("visible", False) else "3",
            },
        )
        first_child_body = next(
            (index for index, child in enumerate(body) if child.tag == "body"),
            len(body),
        )
        body.insert(first_child_body, geom)


def materialize(source: Path, config_path: Path, output: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("unsupported environment schema_version")

    tree = ET.parse(source)
    root = tree.getroot()
    asset = root.find("asset")
    worldbody = root.find("worldbody")
    if asset is None or worldbody is None:
        raise ValueError("MuJoCo model must contain asset and worldbody")

    apply_robot_visual(root, config)
    apply_robot_collision_pads(root, config)

    visual_config = config["visual"]
    visual = root.find("visual")
    if visual is None:
        visual = ET.Element("visual")
        root.insert(1, visual)
    ET.SubElement(
        visual,
        "headlight",
        {
            "ambient": vector(visual_config["ambient"], 3, "visual.ambient"),
            "diffuse": vector(visual_config["diffuse"], 3, "visual.diffuse"),
            "specular": vector(visual_config["specular"], 3, "visual.specular"),
        },
    )
    ET.SubElement(
        visual,
        "rgba",
        {"haze": vector(visual_config["haze_rgba"], 4, "visual.haze_rgba")},
    )

    ET.SubElement(
        asset,
        "texture",
        {
            "name": "workspace_sky",
            "type": "skybox",
            "builtin": "gradient",
            "rgb1": vector(visual_config["sky_rgb_top"], 3, "visual.sky_rgb_top"),
            "rgb2": vector(visual_config["sky_rgb_bottom"], 3, "visual.sky_rgb_bottom"),
            "width": "512",
            "height": "3072",
        },
    )
    floor_config = config["floor"]
    ET.SubElement(
        asset,
        "texture",
        {
            "name": "workspace_floor_grid",
            "type": "2d",
            "builtin": "checker",
            "rgb1": vector(floor_config["checker_rgb1"], 3, "floor.checker_rgb1"),
            "rgb2": vector(floor_config["checker_rgb2"], 3, "floor.checker_rgb2"),
            "width": "512",
            "height": "512",
        },
    )
    ET.SubElement(
        asset,
        "material",
        {
            "name": "workspace_floor_material",
            "texture": "workspace_floor_grid",
            "texrepeat": "8 8",
            "reflectance": "0.08",
        },
    )
    ET.SubElement(
        worldbody,
        "light",
        {
            "name": "workspace_key_light",
            "pos": vector(visual_config["light_pos"], 3, "visual.light_pos"),
            "dir": vector(visual_config["light_dir"], 3, "visual.light_dir"),
            "directional": "true",
            "diffuse": "0.9 0.9 0.9",
            "specular": "0.2 0.2 0.2",
        },
    )
    ET.SubElement(
        worldbody,
        "geom",
        {
            "name": "workspace_floor",
            "type": "plane",
            "size": vector(floor_config["half_size_m"], 3, "floor.half_size_m"),
            "material": "workspace_floor_material",
            "friction": vector(floor_config["friction"], 3, "floor.friction"),
            "condim": "4",
        },
    )

    names: set[str] = set()
    for obstacle in config["obstacles"]:
        name = obstacle["name"]
        if name in names:
            raise ValueError(f"duplicate obstacle name: {name}")
        names.add(name)
        if obstacle.get("type") != "box":
            raise ValueError(f"unsupported obstacle type: {obstacle.get('type')}")
        ET.SubElement(
            worldbody,
            "geom",
            {
                "name": name,
                "type": "box",
                "pos": vector(obstacle["pos_m"], 3, f"{name}.pos_m"),
                "size": vector(obstacle["half_size_m"], 3, f"{name}.half_size_m"),
                "rgba": vector(obstacle["rgba"], 4, f"{name}.rgba"),
                "friction": vector(obstacle["friction"], 3, f"{name}.friction"),
                "condim": "4",
                "contype": "1",
                "conaffinity": "1",
            },
        )

    for dynamic_object in config.get("dynamic_objects", []):
        name = dynamic_object["name"]
        if name in names:
            raise ValueError(f"duplicate environment object name: {name}")
        names.add(name)
        if dynamic_object.get("type") != "box":
            raise ValueError(
                f"unsupported dynamic object type: {dynamic_object.get('type')}"
            )
        body = ET.SubElement(
            worldbody,
            "body",
            {
                "name": name,
                "pos": vector(dynamic_object["pos_m"], 3, f"{name}.pos_m"),
            },
        )
        ET.SubElement(body, "freejoint", {"name": f"{name}_freejoint"})
        ET.SubElement(
            body,
            "geom",
            {
                "name": f"{name}_geom",
                "type": "box",
                "size": vector(
                    dynamic_object["half_size_m"],
                    3,
                    f"{name}.half_size_m",
                ),
                "mass": str(float(dynamic_object["mass_kg"])),
                "rgba": vector(dynamic_object["rgba"], 4, f"{name}.rgba"),
                "friction": vector(
                    dynamic_object["friction"], 3, f"{name}.friction"
                ),
                "condim": "4",
                "contype": "1",
                "conaffinity": "1",
            },
        )

    ET.indent(tree, space="  ")
    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output, encoding="utf-8", xml_declaration=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    materialize(args.source.resolve(), args.config.resolve(), args.output.resolve())
    print(f"Generated arm workspace: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
