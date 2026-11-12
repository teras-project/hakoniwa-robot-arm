#!/usr/bin/env python3
"""Replace the excavator plane with a Recipe-defined HField work pit."""

from __future__ import annotations

import argparse
import json
import math
import struct
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TerrainConfig:
    enabled: bool
    resolution: tuple[int, int]
    size_m: tuple[float, float]
    max_depth_m: float
    pit_center_m: tuple[float, float]
    floor_radius_m: tuple[float, float]
    rim_radius_m: tuple[float, float]
    color_rgba: tuple[float, float, float, float]
    friction: tuple[float, float, float]


def finite_numbers(value: Any, length: int, name: str) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"{name} must contain exactly {length} numbers")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{name} must contain only finite numbers")
    return result


def load_config(path: Path) -> TerrainConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("terrain schema_version must be 1")
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("terrain enabled must be a boolean")
    resolution_value = payload.get("resolution")
    if (
        not isinstance(resolution_value, list)
        or len(resolution_value) != 2
        or any(not isinstance(value, int) for value in resolution_value)
        or any(not 17 <= value <= 1025 for value in resolution_value)
    ):
        raise ValueError("terrain resolution must contain two integers in [17, 1025]")
    size_m = finite_numbers(payload.get("size_m"), 2, "terrain size_m")
    if any(value <= 0.0 for value in size_m):
        raise ValueError("terrain size_m values must be positive")
    max_depth_m = float(payload.get("max_depth_m", 0.0))
    if not math.isfinite(max_depth_m) or max_depth_m <= 0.0:
        raise ValueError("terrain max_depth_m must be positive")
    center = finite_numbers(payload.get("pit_center_m"), 2, "pit_center_m")
    floor_radius = finite_numbers(
        payload.get("pit_floor_radius_m"), 2, "pit_floor_radius_m"
    )
    rim_radius = finite_numbers(
        payload.get("pit_rim_radius_m"), 2, "pit_rim_radius_m"
    )
    if any(value <= 0.0 for value in floor_radius):
        raise ValueError("pit_floor_radius_m values must be positive")
    if any(rim <= floor for rim, floor in zip(rim_radius, floor_radius)):
        raise ValueError("each pit_rim_radius_m must exceed pit_floor_radius_m")
    color = finite_numbers(payload.get("color_rgba"), 4, "terrain color_rgba")
    if any(not 0.0 <= value <= 1.0 for value in color):
        raise ValueError("terrain color_rgba values must be in [0, 1]")
    friction = finite_numbers(payload.get("friction"), 3, "terrain friction")
    if any(value < 0.0 for value in friction):
        raise ValueError("terrain friction values must be non-negative")
    return TerrainConfig(
        enabled=enabled,
        resolution=(resolution_value[0], resolution_value[1]),
        size_m=size_m,
        max_depth_m=max_depth_m,
        pit_center_m=center,
        floor_radius_m=floor_radius,
        rim_radius_m=rim_radius,
        color_rgba=color,
        friction=friction,
    )


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(kind)
    checksum = zlib.crc32(payload, checksum) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


def write_grayscale_png(path: Path, width: int, height: int, pixels: bytes) -> None:
    if len(pixels) != width * height:
        raise ValueError("heightmap pixel count does not match resolution")
    scanlines = b"".join(
        b"\x00" + pixels[row * width : (row + 1) * width]
        for row in range(height)
    )
    payload = b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(
        b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    )
    payload += png_chunk(b"IDAT", zlib.compress(scanlines, level=9))
    payload += png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def smoothstep(value: float) -> float:
    value = min(1.0, max(0.0, value))
    return value * value * (3.0 - 2.0 * value)


def height_value(x_m: float, y_m: float, config: TerrainConfig) -> float:
    dx = x_m - config.pit_center_m[0]
    dy = y_m - config.pit_center_m[1]
    radius = math.hypot(dx, dy)
    if radius == 0.0:
        return 0.0
    cosine = dx / radius
    sine = dy / radius

    def ellipse_radius(axes: tuple[float, float]) -> float:
        return 1.0 / math.sqrt(
            (cosine / axes[0]) ** 2 + (sine / axes[1]) ** 2
        )

    floor_radius = ellipse_radius(config.floor_radius_m)
    rim_radius = ellipse_radius(config.rim_radius_m)
    return smoothstep((radius - floor_radius) / (rim_radius - floor_radius))


def generate_heightmap(config: TerrainConfig) -> bytes:
    width, height = config.resolution
    size_x, size_y = config.size_m
    values = bytearray()
    for row in range(height):
        y_m = -0.5 * size_y + size_y * row / (height - 1)
        for column in range(width):
            x_m = -0.5 * size_x + size_x * column / (width - 1)
            values.append(round(255.0 * height_value(x_m, y_m, config)))
    return bytes(values)


def fmt(values: tuple[float, ...]) -> str:
    return " ".join(f"{value:.9g}" for value in values)


def add_hfield(
    input_path: Path, config_path: Path, heightmap_path: Path, output_path: Path
) -> None:
    config = load_config(config_path)
    tree = ET.parse(input_path)
    root = tree.getroot()
    asset = root.find("asset")
    worldbody = root.find("worldbody")
    floor = root.find("./worldbody/geom[@name='excavator_floor']")
    if asset is None or worldbody is None or floor is None:
        raise ValueError("excavator MJCF is missing asset, worldbody, or excavator_floor")

    if config.enabled:
        pixels = generate_heightmap(config)
        write_grayscale_png(
            heightmap_path, config.resolution[0], config.resolution[1], pixels
        )
        ET.SubElement(
            asset,
            "hfield",
            {
                "name": "excavator_worksite_hfield",
                "file": heightmap_path.name,
                "size": fmt(
                    (
                        0.5 * config.size_m[0],
                        0.5 * config.size_m[1],
                        config.max_depth_m,
                        0.1,
                    )
                ),
            },
        )
        floor.set("type", "hfield")
        floor.attrib.pop("size", None)
        floor.set("hfield", "excavator_worksite_hfield")
        floor.set("pos", f"0 0 {-config.max_depth_m:.9g}")
        floor.set("rgba", fmt(config.color_rgba))
        floor.set("friction", fmt(config.friction))
    else:
        heightmap_path.unlink(missing_ok=True)

    ET.indent(tree, space="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replace the excavator floor with a Recipe-defined HField pit"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--heightmap-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        add_hfield(
            args.input.resolve(),
            args.config.resolve(),
            args.heightmap_output.resolve(),
            args.output.resolve(),
        )
    except (OSError, json.JSONDecodeError, ET.ParseError, ValueError) as error:
        parser.error(str(error))
    print(f"Generated excavator HField: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
