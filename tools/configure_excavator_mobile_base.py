#!/usr/bin/env python3
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path


WHEEL_Y_POSITIONS = (-3.6, -1.4, 0.8)
WHEEL_X = 2.05
WHEEL_Z = -0.65
WHEEL_RADIUS = 0.62
WHEEL_HALF_WIDTH = 0.18
WHEEL_VELOCITY_GAIN = 20000.0
WHEEL_FORCE_LIMIT = 100000.0
HOME_ARM_POSITION = (0.0, 0.6, 0.0, -1.5)
EXCAVATOR_YELLOW = "0.95 0.62 0.05 1"
CRAWLER_DARK = "0.10 0.11 0.12 1"
ARM_POSITION_GAINS = {
    "base_chassis_joint_motor": 10_000_000.0,
    "chassis_boom_joint_motor": 10_000_000.0,
    "boom_stick_joint_motor": 5_000_000.0,
    "stick_bucket_joint_motor": 2_000_000.0,
}


def add_mobile_base(input_path: Path, output_path: Path) -> None:
    tree = ET.parse(input_path)
    root = tree.getroot()
    asset = root.find("asset")
    worldbody = root.find("worldbody")
    actuator = root.find("actuator")
    base = root.find("./worldbody/body[@name='base_link']")
    if asset is None or worldbody is None or actuator is None or base is None:
        raise ValueError("excavator MJCF is missing asset, worldbody, actuator, or base_link")
    if base.find("freejoint") is not None:
        raise ValueError("excavator base already contains a freejoint")

    # The upstream model points along local +Y. Rotate it so that ROS linear.x
    # moves along world +X at the initial pose, and lift the crawler onto the floor.
    base.set("pos", "0 0 1.32")
    base.set("quat", "0.7071067812 0 0 -0.7071067812")
    base.insert(0, ET.Element("freejoint", {"name": "base_freejoint"}))

    # Viewer presentation is part of the reproducible Recipe: a daylight sky,
    # brighter global illumination, and a brown work-site floor.
    ET.SubElement(
        asset,
        "texture",
        {
            "name": "excavator_sky",
            "type": "skybox",
            "builtin": "gradient",
            "rgb1": "0.45 0.65 0.85",
            "rgb2": "0.08 0.12 0.20",
            "width": "512",
            "height": "3072",
        },
    )
    visual = ET.Element("visual")
    ET.SubElement(
        visual,
        "headlight",
        {
            "ambient": "0.45 0.45 0.45",
            "diffuse": "0.85 0.85 0.85",
            "specular": "0.20 0.20 0.20",
        },
    )
    ET.SubElement(visual, "rgba", {"haze": "0.35 0.48 0.62 1"})
    root.insert(2, visual)

    # Preserve the original CAD for rendering. The crawler and chassis collision
    # meshes overlap the floor in the source zero pose, so the hidden wheels own
    # base contact. Boom/stick/bucket collision meshes stay enabled: the bucket
    # must not pass through the work-site floor.
    for body in base.iter("body"):
        body_name = body.get("name", "")
        for geom in body.findall("geom"):
            if geom.get("type") != "mesh":
                continue
            is_visual = geom.get("group") == "1" and geom.get("density") == "0"
            is_base = body_name in {"base_link", "base_chassis_link"}
            if body_name == "base_link":
                geom.set("rgba", CRAWLER_DARK)
            else:
                geom.set("rgba", EXCAVATOR_YELLOW)
            if is_visual:
                geom.set("contype", "0")
                geom.set("conaffinity", "0")
            elif is_base:
                geom.set("contype", "0")
                geom.set("conaffinity", "0")
                geom.set("rgba", "0.10 0.11 0.12 0")
                geom.set("group", "3")
            else:
                geom.set("contype", "1")
                geom.set("conaffinity", "1")
                geom.set("rgba", "0.95 0.62 0.05 0")
                geom.set("group", "3")

    floor = ET.Element(
        "geom",
        {
            "name": "excavator_floor",
            "type": "plane",
            "size": "30 30 0.1",
            "rgba": "0.38 0.25 0.12 1",
            "friction": "1.2 0.02 0.001",
            "condim": "4",
        },
    )
    worldbody.insert(0, floor)
    worldbody.insert(
        1,
        ET.Element(
            "light",
            {
                "name": "excavator_daylight",
                "directional": "true",
                "pos": "0 0 12",
                "dir": "-0.25 -0.35 -1",
                "diffuse": "0.80 0.78 0.72",
                "ambient": "0.25 0.25 0.25",
                "specular": "0.15 0.15 0.15",
                "castshadow": "true",
            },
        ),
    )

    # The upstream roughly 170 t model originally needed very stiff position
    # servos in the small arm-only model. With hundreds of particles MuJoCo
    # selects a sparse Jacobian, where those gains make the coupled system
    # poorly conditioned and lift the chassis. These Recipe-owned gains retain
    # gravity holding while keeping dense and sparse executions consistent.
    for position_actuator in actuator.findall("position"):
        name = position_actuator.get("name", "")
        if name in ARM_POSITION_GAINS:
            position_actuator.set("kp", f"{ARM_POSITION_GAINS[name]:.9g}")

    for side, x_position in (("left", -WHEEL_X), ("right", WHEEL_X)):
        for index, y_position in enumerate(WHEEL_Y_POSITIONS, start=1):
            joint_name = f"{side}_track_wheel_{index}_joint"
            body = ET.SubElement(
                base,
                "body",
                {
                    "name": f"{side}_track_wheel_{index}",
                    "pos": f"{x_position:.6g} {y_position:.6g} {WHEEL_Z:.6g}",
                },
            )
            ET.SubElement(
                body,
                "joint",
                {
                    "name": joint_name,
                    "type": "hinge",
                    "axis": "1 0 0",
                    "damping": "1000",
                    "frictionloss": "100",
                },
            )
            ET.SubElement(
                body,
                "geom",
                {
                    "name": f"{side}_track_wheel_{index}_geom",
                    "type": "cylinder",
                    "size": f"{WHEEL_RADIUS:.6g} {WHEEL_HALF_WIDTH:.6g}",
                    "quat": "0.7071067812 0 0.7071067812 0",
                    "mass": "250",
                    "rgba": "0.08 0.10 0.12 0.06",
                    # The center pair transfers drive force. The end pairs
                    # stabilize the long chassis with low sliding friction so
                    # skid-steer rotation is not locked by six contact patches.
                    "friction": (
                        "1.2 0.02 0.001" if index == 2
                        else "0.08 0.005 0.0005"
                    ),
                    "condim": "4",
                    "priority": "1",
                    "group": "3",
                },
            )
            ET.SubElement(
                actuator,
                "velocity",
                {
                    "name": f"{side}_track_wheel_{index}_motor",
                    "joint": joint_name,
                    # Sized for this roughly 170 t source model. The previous
                    # multi-meganewton servo impulse launched the chassis when
                    # a step-shaped Twist command arrived.
                    "kv": f"{WHEEL_VELOCITY_GAIN:.6g}",
                    "ctrllimited": "true",
                    "ctrlrange": "-8 8",
                    "forcelimited": "true",
                    "forcerange": (
                        f"{-WHEEL_FORCE_LIMIT:.6g} {WHEEL_FORCE_LIMIT:.6g}"
                    ),
                },
            )

    # mj_resetDataKeyframe applies this Recipe-defined safe pose both at startup
    # and on reset. qpos contains free-base(7), arm(4), then six wheel hinges.
    keyframe = ET.SubElement(root, "keyframe")
    ET.SubElement(
        keyframe,
        "key",
        {
            "name": "excavator_home",
            "qpos": " ".join(
                str(value)
                for value in (
                    0.0,
                    0.0,
                    1.32,
                    0.7071067812,
                    0.0,
                    0.0,
                    -0.7071067812,
                    *HOME_ARM_POSITION,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                )
            ),
            "ctrl": " ".join(
                str(value) for value in (*HOME_ARM_POSITION, 0, 0, 0, 0, 0, 0)
            ),
        },
    )

    ET.indent(tree, space="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add a six-wheel differential mobile base to the excavator MJCF"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        add_mobile_base(args.input.resolve(), args.output.resolve())
    except (OSError, ET.ParseError, ValueError) as error:
        parser.error(str(error))
    print(f"Configured excavator mobile base: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
