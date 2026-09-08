#!/usr/bin/env python3
"""Normalize DOBOT Nova5's ROS/Gazebo description for ROS-free MBody use."""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from pathlib import Path


FIND_URI = re.compile(r"^file://\$\(find\s+cra_description\)/(.*)$")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def normalize(input_path: Path, output_path: Path) -> tuple[int, int]:
    tree = ET.parse(input_path)
    root = tree.getroot()

    removed = 0
    for child in list(root):
        if local_name(child.tag) in {"gazebo", "ros2_control"}:
            root.remove(child)
            removed += 1

    rewritten = 0
    for element in root.iter():
        if local_name(element.tag) != "mesh":
            continue
        filename = element.get("filename", "")
        match = FIND_URI.match(filename)
        if match:
            element.set("filename", f"package://cra_description/{match.group(1)}")
            rewritten += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return removed, rewritten


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove ROS/Gazebo-only Nova5 elements and normalize mesh URIs."
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", "-o", required=True, type=Path)
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"input does not exist: {args.input}")

    removed, rewritten = normalize(args.input.resolve(), args.output.resolve())
    if rewritten == 0:
        parser.error("no Nova5 mesh URI was rewritten; upstream format may have changed")

    print(f"Normalized Nova5 URDF: {args.output.resolve()}")
    print(f"  - removed ROS/Gazebo elements: {removed}")
    print(f"  - rewritten mesh URIs: {rewritten}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
