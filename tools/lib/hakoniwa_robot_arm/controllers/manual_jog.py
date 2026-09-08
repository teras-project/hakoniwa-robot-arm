"""Reference device-independent position-jog controller."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Optional

from .gamepad import NormalizedGamepadState


def shape_axis(value: float, deadzone: float, expo: float) -> float:
    magnitude = abs(value)
    if magnitude <= deadzone:
        return 0.0
    normalized = min(1.0, (magnitude - deadzone) / (1.0 - deadzone))
    shaped = (1.0 - expo) * normalized + expo * normalized**3
    return math.copysign(shaped, value)


@dataclass(frozen=True)
class JogResult:
    joint_names: tuple[str, ...]
    positions: tuple[float, ...]
    bank_id: str


class ManualJogController:
    """Integrate normalized stick input into bounded joint position targets."""

    def __init__(
        self,
        mapping: dict,
        joint_limits: Mapping[str, tuple[float, float]],
    ) -> None:
        spec = mapping["spec"]
        if mapping.get("schema_version") != 1:
            raise ValueError("unsupported manual mapping schema_version")
        self._manual_enable_button = spec.get(
            "manual_enable_button", spec.get("deadman_button")
        )
        if not self._manual_enable_button:
            raise ValueError("manual mapping requires manual_enable_button")
        self._deadzone = float(spec["deadzone"])
        self._expo = float(spec["expo"])
        self._banks = tuple(spec["banks"])
        self._joint_names = tuple(joint_limits)
        self._limits = dict(joint_limits)
        self._targets: Optional[dict[str, float]] = None
        self._active = False

        if not 0.0 <= self._deadzone < 1.0 or not 0.0 <= self._expo <= 1.0:
            raise ValueError("deadzone and expo must be within range")
        if not self._banks:
            raise ValueError("manual mapping must contain at least one bank")
        for bank in self._banks:
            for binding in bank["bindings"]:
                joint = binding["joint"]
                if joint not in self._limits:
                    raise ValueError(f"manual mapping references unknown joint: {joint}")
                if float(binding["velocity_rad_s"]) <= 0.0:
                    raise ValueError("joint jog velocity must be positive")

    def _select_bank(self, state: NormalizedGamepadState) -> dict:
        selected = [
            bank
            for bank in self._banks
            if bank.get("select_button") is not None
            and state.buttons.get(bank["select_button"], False)
        ]
        if len(selected) > 1:
            raise ValueError("multiple manual banks are selected")
        if selected:
            return selected[0]
        defaults = [bank for bank in self._banks if bank.get("select_button") is None]
        if len(defaults) != 1:
            raise ValueError("manual mapping must define exactly one default bank")
        return defaults[0]

    def update(
        self,
        state: NormalizedGamepadState,
        current_positions: Mapping[str, float],
        delta_time_sec: float,
    ) -> Optional[JogResult]:
        """Return a target while Manual Enable is held; otherwise return ``None``."""

        if not state.buttons.get(self._manual_enable_button, False):
            self._active = False
            self._targets = None
            return None
        if delta_time_sec <= 0.0:
            raise ValueError("manual controller delta time must be positive")
        if not self._active:
            if set(current_positions) != set(self._joint_names):
                raise ValueError("current JointState does not match manual mapping")
            self._targets = dict(current_positions)
            self._active = True

        assert self._targets is not None
        bank = self._select_bank(state)
        for binding in bank["bindings"]:
            joint = binding["joint"]
            raw = state.axes.get(binding["axis"], 0.0)
            direction = -1.0 if binding.get("invert", False) else 1.0
            velocity = (
                shape_axis(raw, self._deadzone, self._expo)
                * float(binding["velocity_rad_s"])
                * direction
            )
            lower, upper = self._limits[joint]
            self._targets[joint] = max(
                lower,
                min(upper, self._targets[joint] + velocity * delta_time_sec),
            )

        return JogResult(
            joint_names=self._joint_names,
            positions=tuple(self._targets[name] for name in self._joint_names),
            bank_id=bank["id"],
        )
