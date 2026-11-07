#!/usr/bin/env python3
"""Add simple free-body spheres to an excavator worksite MJCF."""

from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SoilConfig:
    enabled: bool
    grid_count: tuple[int, int, int]
    spacing_m: float
    radius_m: float
    center_xy_m: tuple[float, float]
    bottom_z_m: float
    density_kg_m3: float
    contact_condim: int
    friction: tuple[float, float, float]
    color_rgba: tuple[float, float, float, float]

    @property
    def particle_count(self) -> int:
        return math.prod(self.grid_count) if self.enabled else 0


def finite_numbers(value: Any, length: int, name: str) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"{name} must contain exactly {length} numbers")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{name} must contain only finite numbers")
    return result


def load_config(path: Path) -> SoilConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("soil schema_version must be 1")
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("soil enabled must be a boolean")
    grid_value = payload.get("grid_count")
    if (
        not isinstance(grid_value, list)
        or len(grid_value) != 3
        or any(not isinstance(value, int) for value in grid_value)
        or any(not 1 <= value <= 50 for value in grid_value)
    ):
        raise ValueError("soil grid_count must contain three integers in [1, 50]")
    grid_count = (grid_value[0], grid_value[1], grid_value[2])
    if math.prod(grid_count) > 10000:
        raise ValueError("soil grid_count product must not exceed 10000")
    spacing_m = float(payload.get("spacing_m", 0.0))
    radius_m = float(payload.get("particle_radius_m", 0.0))
    if not math.isfinite(radius_m) or not 0.01 <= radius_m <= 1.0:
        raise ValueError("soil particle_radius_m must be in [0.01, 1.0]")
    if not math.isfinite(spacing_m) or spacing_m <= 2.0 * radius_m:
        raise ValueError("soil spacing_m must exceed one particle diameter")
    center_xy_m = finite_numbers(payload.get("center_xy_m"), 2, "soil center_xy_m")
    bottom_z_m = float(payload.get("bottom_z_m", 0.0))
    if not math.isfinite(bottom_z_m):
        raise ValueError("soil bottom_z_m must be finite")
    density = float(payload.get("density_kg_m3", 0.0))
    if not math.isfinite(density) or density <= 0.0:
        raise ValueError("soil density_kg_m3 must be positive")
    contact_condim = payload.get("contact_condim")
    if contact_condim not in (1, 3, 4, 6):
        raise ValueError("soil contact_condim must be one of 1, 3, 4, or 6")
    friction = finite_numbers(payload.get("friction"), 3, "soil friction")
    if any(value < 0.0 for value in friction):
        raise ValueError("soil friction values must be non-negative")
    color = finite_numbers(payload.get("color_rgba"), 4, "soil color_rgba")
    if any(not 0.0 <= value <= 1.0 for value in color):
        raise ValueError("soil color_rgba values must be in [0, 1]")
    return SoilConfig(
        enabled=enabled,
        grid_count=grid_count,
        spacing_m=spacing_m,
        radius_m=radius_m,
        center_xy_m=center_xy_m,
        bottom_z_m=bottom_z_m,
        density_kg_m3=density,
        contact_condim=contact_condim,
        friction=(friction[0], friction[1], friction[2]),
        color_rgba=color,
    )


def fmt(values: tuple[float, ...] | list[float]) -> str:
    return " ".join(f"{value:.9g}" for value in values)


def configure_particle_solver(root: ET.Element) -> None:
    # Keep the existing solver contract for the roughly 170 t excavator's stiff
    # position servos. MuJoCo's auto Jacobian selection chooses sparse storage
    # for this high-DoF model without changing the coupled plant numerics.
    option = root.find("option")
    size = root.find("size")
    if size is None:
        size = ET.Element("size", {"memory": "512M"})
        root.insert((list(root).index(option) + 1) if option is not None else 0, size)
    else:
        size.set("memory", "512M")


def particle_positions(config: SoilConfig) -> list[tuple[float, float, float]]:
    nx, ny, nz = config.grid_count
    span_x = (nx - 1) * config.spacing_m
    span_y = (ny - 1) * config.spacing_m
    start = (
        config.center_xy_m[0] - 0.5 * span_x,
        config.center_xy_m[1] - 0.5 * span_y,
        config.bottom_z_m,
    )
    return [
        (
            start[0] + x_index * config.spacing_m,
            start[1] + y_index * config.spacing_m,
            start[2] + z_index * config.spacing_m,
        )
        for z_index in range(nz)
        for y_index in range(ny)
        for x_index in range(nx)
    ]


def add_free_spheres(
    worldbody: ET.Element,
    config: SoilConfig,
    positions: list[tuple[float, float, float]],
) -> None:
    for index, position in enumerate(positions, start=1):
        name = f"excavator_soil_sphere_{index:03d}"
        particle = ET.SubElement(
            worldbody,
            "body",
            {"name": name, "pos": fmt(position)},
        )
        ET.SubElement(
            particle,
            "freejoint",
            {"name": f"{name}_freejoint"},
        )
        ET.SubElement(
            particle,
            "geom",
            {
                "name": f"{name}_geom",
                "type": "sphere",
                "size": f"{config.radius_m:.9g}",
                "density": f"{config.density_kg_m3:.9g}",
                "rgba": fmt(config.color_rgba),
                "condim": str(config.contact_condim),
                "friction": fmt(config.friction),
                "contype": "1",
                "conaffinity": "1",
                "group": "2",
            },
        )


def extend_keyframes(
    root: ET.Element,
    positions: list[tuple[float, float, float]],
) -> None:
    if not positions:
        return
    particle_qpos = " ".join(
        f"{fmt(position)} 1 0 0 0" for position in positions
    )
    for key in root.findall("./keyframe/key"):
        qpos = key.get("qpos")
        if qpos is not None:
            key.set("qpos", f"{qpos} {particle_qpos}")


def add_soil(input_path: Path, config_path: Path, output_path: Path) -> int:
    config = load_config(config_path)
    tree = ET.parse(input_path)
    root = tree.getroot()
    worldbody = root.find("worldbody")
    if worldbody is None:
        raise ValueError("excavator MJCF is missing worldbody")
    if root.find(".//body[@name='excavator_soil_sphere_001']") is not None:
        raise ValueError("excavator MJCF already contains generated soil")
    positions: list[tuple[float, float, float]] = []
    if config.enabled:
        configure_particle_solver(root)
        positions = particle_positions(config)
        add_free_spheres(worldbody, config, positions)
    extend_keyframes(root, positions)
    ET.indent(tree, space="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return config.particle_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add simple MuJoCo free-body soil spheres to the excavator MJCF"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        count = add_soil(
            args.input.resolve(), args.config.resolve(), args.output.resolve()
        )
    except (OSError, json.JSONDecodeError, ET.ParseError, ValueError) as error:
        parser.error(str(error))
    print(f"Generated excavator soil particles: {args.output} particles={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
