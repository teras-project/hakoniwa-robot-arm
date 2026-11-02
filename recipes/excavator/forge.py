#!/usr/bin/env python3
"""Forge the excavator runtime models without a shell dependency."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = PACK_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from _hakoniwa_composer import (  # noqa: E402
    HakoniwaComposerError,
    excavator_bucket_proxy_python,
    model_forge_root,
    model_install_dir,
    model_install_staging_dir,
    publish_model_install,
)

ROBOT_ID = "excavator"
RECIPE_DIR = PACK_ROOT / "recipes" / ROBOT_ID
SOURCE_YAML = PACK_ROOT / "sources/models/excavator/source.yaml"
CHECKSUM_FILES = (
    "LICENSE",
    "excavator.runtime.xml",
    "excavator.mobile.xml",
    "excavator.bucket.xml",
    "excavator.bucket-proxy-debug.xml",
    "excavator.terrain.xml",
    "excavator.soil.xml",
    "excavator-worksite-height.png",
    "model/urdf/excavator.urdf",
)


def _mbody_root() -> Path:
    configured = os.environ.get("HAKONIWA_MBODY_REGISTRY_ROOT", "").strip()
    return (Path(configured).expanduser().resolve() if configured else
            (PACK_ROOT.parent / "hakoniwa-mbody-registry").resolve())


def _run(python: Path, script: Path, *args: object) -> None:
    command = [str(python), str(script), *(str(arg) for arg in args)]
    print("+", subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=PACK_ROOT, check=True)


def _reset(path: Path) -> None:
    if path.exists() or path.is_symlink():
        shutil.rmtree(path) if path.is_dir() and not path.is_symlink() else path.unlink()
    path.mkdir(parents=True)


def _copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise HakoniwaComposerError(f"required file not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def checksum_names(build_dir: Path) -> tuple[str, ...]:
    meshes = tuple(
        path.relative_to(build_dir).as_posix()
        for path in sorted((build_dir / "model/meshes").iterdir(), key=lambda item: item.name)
        if path.is_file()
    )
    return CHECKSUM_FILES + meshes


def write_sha256sums(build_dir: Path, names: tuple[str, ...]) -> Path:
    output = build_dir / "SHA256SUMS"
    lines = [f"{hashlib.sha256((build_dir / name).read_bytes()).hexdigest()}  {name}" for name in names]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


def forge() -> Path:
    mbody = _mbody_root()
    fetch = mbody / "tools/fetch.py"
    if not fetch.is_file():
        raise HakoniwaComposerError(f"hakoniwa-mbody-registry sibling checkout was not found: {mbody}")
    bucket_python = excavator_bucket_proxy_python()
    if not bucket_python.is_file():
        raise HakoniwaComposerError(
            "Recipe-owned bucket proxy environment was not found: "
            f"{bucket_python}; run: python tools/install_excavator_bucket_proxy_tools.py"
        )

    forge_root = model_forge_root(ROBOT_ID)
    source = forge_root / "source"
    build = forge_root / "build"
    staging = model_install_staging_dir(ROBOT_ID)
    output = model_install_dir(ROBOT_ID)
    for directory in (source, build, staging):
        _reset(directory)

    print("=== Excavator Forge: Fetch Pinned Source ===")
    _run(Path(sys.executable), fetch, SOURCE_YAML, "--output-dir", source)
    upstream = source / "ExcavatorCADFiles/URDF_MathScavator9000_flat/MathScavator9000_flat"
    model = build / "model"
    urdf = model / "urdf/excavator.urdf"

    steps: tuple[tuple[str, Path, Path, tuple[object, ...]], ...] = (
        ("Normalize URDF Meshes", Path(sys.executable), PACK_ROOT / "tools/normalize_excavator_model.py", (upstream, model)),
        ("Convert URDF to MJCF", Path(sys.executable), mbody / "tools/urdf2mjcf.py", (urdf, "--package-root", f"MathScavator9000_flat.SLDASM={model}", "--output", build / "excavator.xml")),
        ("Add Position Actuators", Path(sys.executable), mbody / "tools/mjcf_add_actuators.py", (build / "excavator.xml", RECIPE_DIR / "actuator.yaml", "--output", build / "excavator.actuated.xml")),
        ("Configure Stable Integration", Path(sys.executable), PACK_ROOT / "tools/configure_mjcf_options.py", (build / "excavator.actuated.xml", "--timestep", "0.002", "--integrator", "implicitfast", "--output", build / "excavator.stabilized.xml")),
        ("Exclude Adjacent Joint Contacts", Path(sys.executable), mbody / "tools/mjcf_add_contact_excludes.py", (build / "excavator.stabilized.xml", RECIPE_DIR / "contact-excludes.yaml", "--output", build / "excavator.runtime.xml")),
        ("Add Six-wheel Differential Base", Path(sys.executable), PACK_ROOT / "tools/configure_excavator_mobile_base.py", (build / "excavator.runtime.xml", "--output", build / "excavator.mobile.xml")),
        ("Add Open Bucket Collision Shell", bucket_python, PACK_ROOT / "tools/generate_excavator_bucket_collision.py", (build / "excavator.mobile.xml", "--config", RECIPE_DIR / "bucket-collision.yaml", "--debug-output", build / "excavator.bucket-proxy-debug.xml", "--output", build / "excavator.bucket.xml")),
        ("Add HField Work Pit", Path(sys.executable), PACK_ROOT / "tools/generate_excavator_hfield.py", (build / "excavator.bucket.xml", "--config", RECIPE_DIR / "config/environment/terrain.json", "--heightmap-output", build / "excavator-worksite-height.png", "--output", build / "excavator.terrain.xml")),
        ("Add Simplified Granular Soil", Path(sys.executable), PACK_ROOT / "tools/generate_excavator_soil.py", (build / "excavator.terrain.xml", "--config", RECIPE_DIR / "config/environment/soil.json", "--output", build / "excavator.soil.xml")),
    )
    for index, (label, python, script, args) in enumerate(steps):
        print(f"\n=== Excavator Forge: {label} ===")
        _run(python, script, *args)
        if index == 0:
            _copy_file(source / "license.txt", build / "LICENSE")

    write_sha256sums(build, checksum_names(build))
    shutil.copytree(build, staging, dirs_exist_ok=True, symlinks=True)
    published = publish_model_install(ROBOT_ID)
    print("\nExcavator forge complete.")
    for label, name in (("runtime MJCF", "excavator.runtime.xml"), ("mobile MJCF", "excavator.mobile.xml"), ("bucket MJCF", "excavator.bucket.xml"), ("debug MJCF", "excavator.bucket-proxy-debug.xml"), ("terrain MJCF", "excavator.terrain.xml"), ("soil MJCF", "excavator.soil.xml"), ("source model", "model"), ("checksums", "SHA256SUMS")):
        print(f"  - {label + ':':14} {output / name}")
    return published


def main() -> int:
    try:
        forge()
        return 0
    except subprocess.CalledProcessError as error:
        print(f"error: Excavator forge tool failed with exit code {error.returncode}: {subprocess.list2cmdline(error.cmd)}", file=sys.stderr)
        return error.returncode or 1
    except (HakoniwaComposerError, OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
