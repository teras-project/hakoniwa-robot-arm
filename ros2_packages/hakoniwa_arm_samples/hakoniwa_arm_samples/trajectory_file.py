from __future__ import annotations

import json
import math
from pathlib import Path


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def load_trajectory_file(path: Path) -> tuple[list[str], list[dict[str, object]]]:
    try:
        payload = json.loads(path.expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"failed to read trajectory file {path}: {error}") from error

    if not isinstance(payload, dict):
        raise ValueError("trajectory file must contain a JSON object")
    joint_names = payload.get("joint_names")
    points = payload.get("points")
    if (
        not isinstance(joint_names, list)
        or not joint_names
        or any(not isinstance(name, str) or not name for name in joint_names)
    ):
        raise ValueError("trajectory joint_names must be a non-empty string array")
    if len(set(joint_names)) != len(joint_names):
        raise ValueError("trajectory joint_names must be unique")
    if not isinstance(points, list) or not points:
        raise ValueError("trajectory points must be a non-empty array")

    normalized: list[dict[str, object]] = []
    previous_time = -1.0
    for index, point in enumerate(points):
        label = f"trajectory points[{index}]"
        if not isinstance(point, dict):
            raise ValueError(f"{label} must be an object")
        time_from_start = _finite_number(
            point.get("time_from_start"), f"{label}.time_from_start"
        )
        if time_from_start < 0.0:
            raise ValueError(f"{label}.time_from_start must be non-negative")
        if time_from_start <= previous_time:
            raise ValueError("trajectory point times must be strictly increasing")
        positions = point.get("positions")
        if not isinstance(positions, list) or len(positions) != len(joint_names):
            raise ValueError(
                f"{label}.positions must contain {len(joint_names)} values"
            )
        normalized_positions = [
            _finite_number(value, f"{label}.positions[{position_index}]")
            for position_index, value in enumerate(positions)
        ]
        normalized.append(
            {
                "time_from_start": time_from_start,
                "positions": normalized_positions,
            }
        )
        previous_time = time_from_start
    return list(joint_names), normalized
