#!/usr/bin/env python3
"""Render reference-only STL sections with the human-authored YAML proxy."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import trimesh

from generate_excavator_bucket_collision import (
    PART_NAMES,
    load_bucket_collision,
    matrix_multiply,
    rpy_deg_matrix,
    transform_part,
)


SECTION_X_M = (-0.50, 0.0, 0.50)
PLOT_Y_RANGE = (-1.95, 1.75)
PLOT_Z_RANGE = (-1.25, 1.35)


def triangle_plane_segments(mesh: trimesh.Trimesh, x_m: float):
    segments = []
    vertices = np.asarray(mesh.vertices)
    for face in np.asarray(mesh.faces):
        triangle = vertices[face]
        points = []
        for start, end in ((0, 1), (1, 2), (2, 0)):
            x0 = triangle[start, 0] - x_m
            x1 = triangle[end, 0] - x_m
            if abs(x0) < 1e-12 and abs(x1) < 1e-12:
                continue
            if x0 * x1 <= 0.0 and abs(x1 - x0) > 1e-12:
                ratio = -x0 / (x1 - x0)
                if -1e-9 <= ratio <= 1.0 + 1e-9:
                    point = triangle[start] + ratio * (triangle[end] - triangle[start])
                    if not any(np.linalg.norm(point - known) < 1e-7 for known in points):
                        points.append(point)
        if len(points) == 2:
            segments.append((points[0][1:3], points[1][1:3]))
    return segments


def proxy_boxes(config: dict):
    frame_rotation = rpy_deg_matrix(config["frame"]["rpy_deg"])
    boxes = []
    for name in PART_NAMES:
        part = config["parts"][name]
        if not part["enabled"]:
            continue
        position, _ = transform_part(config, part)
        rotation = matrix_multiply(frame_rotation, rpy_deg_matrix(part["rpy_deg"]))
        half = np.asarray(part["dimensions_m"], dtype=float) / 2.0
        corners = []
        for sx in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                for sz in (-1.0, 1.0):
                    local = half * np.asarray([sx, sy, sz])
                    rotated = np.asarray(
                        [
                            sum(rotation[row][column] * local[column] for column in range(3))
                            for row in range(3)
                        ]
                    )
                    corners.append(np.asarray(position) + rotated)
        boxes.append({"name": name, "corners": np.asarray(corners), "rgba": part["rgba"]})
    return boxes


def convex_hull_2d(points):
    unique = sorted({(round(float(p[0]), 9), round(float(p[1]), 9)) for p in points})
    if len(unique) <= 1:
        return unique

    def cross(origin, a, b):
        return (a[0] - origin[0]) * (b[1] - origin[1]) - (
            a[1] - origin[1]
        ) * (b[0] - origin[0])

    lower = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def color_css(rgba):
    red, green, blue, alpha = rgba
    return f"rgba({round(red * 255)},{round(green * 255)},{round(blue * 255)},{alpha})"


def render_svg(mesh, boxes, output_path: Path):
    panel_width, panel_height = 430, 500
    margin_left, margin_top = 55, 52
    plot_width, plot_height = 330, 350

    def project(panel, y_m, z_m):
        x = panel * panel_width + margin_left + (
            (y_m - PLOT_Y_RANGE[0]) / (PLOT_Y_RANGE[1] - PLOT_Y_RANGE[0])
        ) * plot_width
        y = margin_top + plot_height - (
            (z_m - PLOT_Z_RANGE[0]) / (PLOT_Z_RANGE[1] - PLOT_Z_RANGE[0])
        ) * plot_height
        return x, y

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{panel_width * 3}" height="{panel_height}">',
        '<rect width="100%" height="100%" fill="#fff"/>',
        '<style>text{font-family:ui-monospace,monospace;fill:#20242a}.mesh{stroke:#303740;stroke-width:1.2}.axis{stroke:#c3c8cf}.title{font-size:14px;font-weight:600}.note{font-size:11px}</style>',
    ]
    for panel, x_m in enumerate(SECTION_X_M):
        left = panel * panel_width
        svg.append(f'<text class="title" x="{left + margin_left}" y="25">parent Y-Z section: X={x_m:+.2f} m</text>')
        svg.append(f'<rect class="axis" fill="none" x="{left + margin_left}" y="{margin_top}" width="{plot_width}" height="{plot_height}"/>')
        for start, end in triangle_plane_segments(mesh, x_m):
            x1, y1 = project(panel, start[0], start[1])
            x2, y2 = project(panel, end[0], end[1])
            svg.append(f'<line class="mesh" x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}"/>')
        for box in boxes:
            corners = box["corners"]
            if not corners[:, 0].min() <= x_m <= corners[:, 0].max():
                continue
            points = " ".join(
                f'{project(panel, y, z)[0]:.2f},{project(panel, y, z)[1]:.2f}'
                for y, z in convex_hull_2d(corners[:, 1:3])
            )
            color = color_css(box["rgba"])
            svg.append(f'<polygon points="{points}" fill="{color}" stroke="{color}" stroke-width="1.5"/>')
        svg.append(f'<text class="note" x="{left + margin_left}" y="430">gray: STL reference only / color: YAML proxy</text>')
        svg.append(f'<text class="note" x="{left + margin_left}" y="448">No surface semantics are inferred.</text>')
    svg.append("</svg>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(svg) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config_bytes = args.config.read_bytes()
    mesh = trimesh.load_mesh(args.mesh)
    config = load_bucket_collision(args.config)
    render_svg(mesh, proxy_boxes(config), args.output)
    if args.config.read_bytes() != config_bytes:
        raise RuntimeError("analyzer must not modify bucket collision YAML")
    print(f"STL AABB min={mesh.bounds[0].tolist()} max={mesh.bounds[1].tolist()}")
    print("Reference only: no opening, cutting edge, inner surface, or outer surface was inferred.")
    print(f"Wrote YAML overlay: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
