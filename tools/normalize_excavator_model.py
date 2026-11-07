#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import struct
from pathlib import Path


class ModelError(RuntimeError):
    pass


def binary_stl_to_obj(source: Path, destination: Path) -> None:
    """Convert a binary STL to a deterministic indexed OBJ without decimation."""
    with source.open("rb") as stream:
        stream.read(80)
        count_bytes = stream.read(4)
        if len(count_bytes) != 4:
            raise ModelError(f"invalid binary STL header: {source}")
        triangle_count = struct.unpack("<I", count_bytes)[0]

        vertices: list[tuple[float, float, float]] = []
        vertex_ids: dict[tuple[float, float, float], int] = {}
        faces: list[tuple[int, int, int]] = []

        for triangle_index in range(triangle_count):
            record = stream.read(50)
            if len(record) != 50:
                raise ModelError(
                    f"truncated binary STL at triangle {triangle_index}: {source}"
                )
            values = struct.unpack("<12fH", record)
            face: list[int] = []
            for offset in (3, 6, 9):
                vertex = (values[offset], values[offset + 1], values[offset + 2])
                vertex_id = vertex_ids.get(vertex)
                if vertex_id is None:
                    vertex_id = len(vertices) + 1
                    vertex_ids[vertex] = vertex_id
                    vertices.append(vertex)
                face.append(vertex_id)
            faces.append((face[0], face[1], face[2]))

        if stream.read(1):
            raise ModelError(f"binary STL contains trailing data: {source}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="ascii", newline="\n") as stream:
        stream.write("# Converted losslessly from MathWorks binary STL for MuJoCo\n")
        for x, y, z in vertices:
            stream.write(f"v {x:.9g} {y:.9g} {z:.9g}\n")
        for a, b, c in faces:
            stream.write(f"f {a} {b} {c}\n")


def normalize(source_package: Path, destination_package: Path) -> Path:
    source_urdf = (
        source_package / "urdf" / "MathScavator9000_flat.SLDASM.urdf"
    )
    source_meshes = source_package / "meshes"
    if not source_urdf.is_file() or not source_meshes.is_dir():
        raise ModelError(f"upstream excavator URDF package is incomplete: {source_package}")

    if destination_package.exists():
        shutil.rmtree(destination_package)
    (destination_package / "urdf").mkdir(parents=True)
    (destination_package / "meshes").mkdir(parents=True)

    for source_mesh in sorted(source_meshes.glob("*.STL")):
        if source_mesh.name == "base_chassis_link.STL":
            binary_stl_to_obj(
                source_mesh,
                destination_package / "meshes" / "base_chassis_link.obj",
            )
        else:
            shutil.copy2(source_mesh, destination_package / "meshes" / source_mesh.name)

    urdf_text = source_urdf.read_text(encoding="utf-8")
    urdf_text = urdf_text.replace("base_chassis_link.STL", "base_chassis_link.obj")
    urdf_text = "\n".join(line.rstrip() for line in urdf_text.splitlines()) + "\n"
    destination_urdf = destination_package / "urdf" / "excavator.urdf"
    destination_urdf.write_text(urdf_text, encoding="utf-8")

    package_xml = source_package / "package.xml"
    if package_xml.is_file():
        shutil.copy2(package_xml, destination_package / "package.xml")
    return destination_urdf


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize the MathScavator9000 URDF package for MuJoCo"
    )
    parser.add_argument("source_package", type=Path)
    parser.add_argument("destination_package", type=Path)
    args = parser.parse_args()
    try:
        output = normalize(args.source_package.resolve(), args.destination_package.resolve())
    except (ModelError, OSError, struct.error) as error:
        parser.error(str(error))
    print(f"Normalized excavator URDF: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
