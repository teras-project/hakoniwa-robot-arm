#!/usr/bin/env python3
"""Synchronize derived arm joint limits from a source URDF.

The source URDF is the single source of truth.  This tool deliberately updates
only actuator ``ctrlrange`` and Runtime ``spec.limit`` values; actuator type,
gains, bindings, and PDU settings remain recipe-owned.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml


Limit = tuple[float, float]


class JointLimitError(ValueError):
    pass


def read_urdf_limits(path: Path) -> dict[str, Limit]:
    root = ET.parse(path).getroot()
    limits: dict[str, Limit] = {}
    for joint in root.findall(".//joint"):
        joint_type = joint.get("type")
        if joint_type not in {"revolute", "prismatic"}:
            continue
        name = joint.get("name")
        limit = joint.find("limit")
        if not name or limit is None:
            continue
        lower = limit.get("lower")
        upper = limit.get("upper")
        if lower is None or upper is None:
            raise JointLimitError(f"URDF joint {name!r} has no lower/upper limit")
        parsed = (float(lower), float(upper))
        if not parsed[0] < parsed[1]:
            raise JointLimitError(f"URDF joint {name!r} has an invalid limit: {parsed}")
        limits[name] = parsed
    if not limits:
        raise JointLimitError(f"no limited revolute/prismatic joints found in {path}")
    return limits


def read_runtime_overrides(path: Path | None, source: dict[str, Limit]) -> dict[str, Limit]:
    if path is None:
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = payload.get("limits", payload) if isinstance(payload, dict) else None
    if not isinstance(raw, dict):
        raise JointLimitError(f"runtime override file must contain a mapping: {path}")
    overrides: dict[str, Limit] = {}
    for name, value in raw.items():
        if name not in source:
            raise JointLimitError(f"runtime override references unknown URDF joint {name!r}")
        if not isinstance(value, dict) or "lower" not in value or "upper" not in value:
            raise JointLimitError(f"runtime override for {name!r} needs lower and upper")
        limit = (float(value["lower"]), float(value["upper"]))
        if not source[name][0] <= limit[0] < limit[1] <= source[name][1]:
            raise JointLimitError(
                f"runtime override for {name!r} must stay inside the URDF limit {source[name]}"
            )
        overrides[name] = limit
    return overrides


def sync_actuator_yaml(path: Path, source: dict[str, Limit], *, check: bool) -> int:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    actuators = payload.get("actuators") if isinstance(payload, dict) else None
    if not isinstance(actuators, list):
        raise JointLimitError(f"actuator config has no actuators list: {path}")
    changed = 0
    matched = 0
    for actuator in actuators:
        if not isinstance(actuator, dict) or actuator.get("type") != "position":
            continue
        joint = actuator.get("joint")
        if joint not in source:
            raise JointLimitError(f"actuator config references unknown URDF joint {joint!r}: {path}")
        matched += 1
        desired = list(source[joint])
        current = actuator.get("ctrlrange")
        if current != desired:
            if check:
                raise JointLimitError(
                    f"actuator ctrlrange for {joint!r} is {current}, expected {desired}"
                )
            actuator["ctrlrange"] = desired
            changed += 1
    if not matched:
        raise JointLimitError(f"no position actuators found in {path}")
    if changed:
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return changed


def _runtime_files(directory: Path) -> list[Path]:
    files = sorted(directory.glob("*.json"))
    if not files:
        raise JointLimitError(f"no Runtime actuator JSON files found in {directory}")
    return files


def runtime_position_joints(directory: Path) -> set[str]:
    joints: set[str] = set()
    for path in _runtime_files(directory):
        payload = json.loads(path.read_text(encoding="utf-8"))
        spec = payload.get("spec") if isinstance(payload, dict) else None
        if isinstance(spec, dict) and spec.get("type") == "position":
            joint = spec.get("joint_name")
            if isinstance(joint, str):
                joints.add(joint)
    return joints


def sync_runtime_configs(
    directory: Path,
    source: dict[str, Limit],
    overrides: dict[str, Limit],
    *,
    check: bool,
) -> int:
    changed = 0
    matched = 0
    for path in _runtime_files(directory):
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
        spec = payload.get("spec") if isinstance(payload, dict) else None
        if not isinstance(spec, dict) or spec.get("type") != "position":
            continue
        joint = spec.get("joint_name")
        if joint not in source:
            raise JointLimitError(f"Runtime config references unknown URDF joint {joint!r}: {path}")
        matched += 1
        desired = overrides.get(joint, source[joint])
        current = spec.get("limit")
        expected = {"lower": desired[0], "upper": desired[1]}
        if current != expected:
            if check:
                raise JointLimitError(
                    f"Runtime limit for {joint!r} is {current}, expected {expected}"
                )
            spec["limit"] = expected
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            changed += 1
    if not matched:
        raise JointLimitError(f"no position Runtime actuator configs found in {directory}")
    return changed


def _parse_range(raw: str | None, description: str) -> Limit:
    if raw is None:
        raise JointLimitError(f"{description} has no range")
    values = raw.split()
    if len(values) != 2:
        raise JointLimitError(f"{description} has an invalid range: {raw!r}")
    return float(values[0]), float(values[1])


def validate_mjcf(
    path: Path,
    source: dict[str, Limit],
    required_joints: set[str],
    tolerance: float,
) -> None:
    root = ET.parse(path).getroot()
    compiler = root.find("compiler")
    angle = compiler.get("angle", "degree") if compiler is not None else "degree"
    if angle != "radian":
        raise JointLimitError(
            f"MJCF validation expects compiler angle=\"radian\" for URDF limits: {path}"
        )

    joints = {joint.get("name"): joint for joint in root.findall(".//joint") if joint.get("name")}
    positions = {
        actuator.get("joint"): actuator
        for actuator in root.findall("./actuator/position")
        if actuator.get("joint")
    }
    for name in required_joints:
        expected = source[name]
        if name not in joints:
            raise JointLimitError(f"MJCF has no joint for Runtime joint {name!r}: {path}")
        actual = _parse_range(joints[name].get("range"), f"MJCF joint {name!r}")
        if not all(math.isclose(a, e, abs_tol=tolerance, rel_tol=0.0) for a, e in zip(actual, expected)):
            raise JointLimitError(f"MJCF joint range for {name!r} is {actual}, expected {expected}")
        actuator = positions.get(name)
        if actuator is None:
            raise JointLimitError(f"MJCF has no position actuator for Runtime joint {name!r}: {path}")
        actual_ctrl = _parse_range(
            actuator.get("ctrlrange"), f"MJCF position actuator for {name!r}"
        )
        if not all(
            math.isclose(a, e, abs_tol=tolerance, rel_tol=0.0)
            for a, e in zip(actual_ctrl, expected)
        ):
            raise JointLimitError(
                f"MJCF actuator ctrlrange for {name!r} is {actual_ctrl}, expected {expected}"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Synchronize derived arm limits from a source URDF without replacing tuned values."
    )
    parser.add_argument("source_urdf", type=Path)
    parser.add_argument("--runtime-config-dir", required=True, type=Path)
    parser.add_argument("--actuator-yaml", type=Path)
    parser.add_argument("--runtime-limit-overrides", type=Path)
    parser.add_argument("--validate-mjcf", type=Path)
    parser.add_argument("--tolerance", type=float, default=1e-5)
    parser.add_argument("--check", action="store_true", help="validate without writing")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        source = read_urdf_limits(args.source_urdf)
        overrides = read_runtime_overrides(args.runtime_limit_overrides, source)
        runtime_joints = runtime_position_joints(args.runtime_config_dir)
        if args.validate_mjcf is not None:
            validate_mjcf(args.validate_mjcf, source, runtime_joints, args.tolerance)
        changed = 0
        if args.actuator_yaml is not None:
            changed += sync_actuator_yaml(args.actuator_yaml, source, check=args.check)
        changed += sync_runtime_configs(
            args.runtime_config_dir, source, overrides, check=args.check
        )
    except (ET.ParseError, OSError, ValueError, yaml.YAMLError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    action = "validated" if args.check else f"updated {changed} file(s)"
    print(f"joint limits: {action} from {args.source_urdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
