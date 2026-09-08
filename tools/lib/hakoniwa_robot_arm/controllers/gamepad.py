"""Normalize a raw gamepad using an explicit device profile."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class NormalizedGamepadState:
    axes: Mapping[str, float]
    buttons: Mapping[str, bool]


def validate_device(
    profile: dict,
    *,
    os_name: str,
    backend: str,
    device_name: str,
    axis_count: int,
    button_count: int,
) -> None:
    """Fail closed when a profile does not describe the connected device."""

    if profile.get("schema_version") != 1:
        raise ValueError("unsupported device profile schema_version")
    match = profile["match"]
    if match["os"] != os_name or match["backend"] != backend:
        raise ValueError("device profile OS/backend does not match")
    if re.search(match["name_regex"], device_name) is None:
        raise ValueError(f"controller name does not match profile: {device_name}")
    if axis_count < int(match["minimum_axes"]):
        raise ValueError("controller exposes fewer axes than the profile requires")
    if button_count < int(match["minimum_buttons"]):
        raise ValueError("controller exposes fewer buttons than the profile requires")

    for name, spec in profile["axes"].items():
        index = int(spec["index"])
        if index < 0 or index >= axis_count:
            raise ValueError(f"axis {name} index is out of range")
    for name, spec in profile["buttons"].items():
        index = int(spec["index"])
        if index < 0 or index >= button_count:
            raise ValueError(f"button {name} index is out of range")


def normalize(joystick, profile: dict) -> NormalizedGamepadState:
    """Read one canonical state from a pygame-compatible joystick object."""

    axes: dict[str, float] = {}
    for name, spec in profile["axes"].items():
        value = float(joystick.get_axis(int(spec["index"])))
        if spec.get("invert", False):
            value = -value
        axes[name] = max(-1.0, min(1.0, value))

    buttons = {
        name: bool(joystick.get_button(int(spec["index"])))
        for name, spec in profile["buttons"].items()
    }
    return NormalizedGamepadState(axes=axes, buttons=buttons)
