#!/usr/bin/env python3
"""Set explicit simulation options on a generated MJCF model."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure MJCF timestep and integrator")
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", "-o", required=True, type=Path)
    parser.add_argument("--timestep", required=True, type=float)
    parser.add_argument("--integrator", required=True)
    args = parser.parse_args()

    if args.timestep <= 0:
        parser.error("--timestep must be positive")

    tree = ET.parse(args.input)
    root = tree.getroot()
    option = root.find("option")
    if option is None:
        option = ET.Element("option")
        compiler = root.find("compiler")
        root.insert(1 if compiler is not None else 0, option)
    option.set("timestep", str(args.timestep))
    option.set("integrator", args.integrator)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="  ")
    tree.write(args.output, encoding="utf-8", xml_declaration=False)
    print(f"Configured MJCF options: {args.output}")
    print(f"  - timestep: {args.timestep}")
    print(f"  - integrator: {args.integrator}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
