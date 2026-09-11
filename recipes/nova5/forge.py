#!/usr/bin/env python3
"""Forge the Nova5 runtime model without a shell dependency."""

from __future__ import annotations

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
    model_forge_root,
    model_install_dir,
    model_install_staging_dir,
    publish_model_install,
)

ROBOT_ID = "nova5"
RECIPE_DIR = PACK_ROOT / "recipes" / ROBOT_ID
SOURCE_YAML = PACK_ROOT / "sources" / "models" / ROBOT_ID / "source.yaml"


def _mbody_root() -> Path:
    configured = os.environ.get("HAKONIWA_MBODY_REGISTRY_ROOT", "").strip()
    return (
        Path(configured).expanduser().resolve()
        if configured
        else (PACK_ROOT.parent / "hakoniwa-mbody-registry").resolve()
    )


def _run_tool(script: Path, *args: object) -> None:
    command = [sys.executable, str(script), *(str(arg) for arg in args)]
    print("+", subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=PACK_ROOT, check=True)


def _reset_directory(path: Path) -> None:
    if path.exists() or path.is_symlink():
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()
    path.mkdir(parents=True, exist_ok=True)


def _copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise HakoniwaComposerError(f"required directory not found: {source}")
    shutil.copytree(source, destination, dirs_exist_ok=True, symlinks=True)


def _copy_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise HakoniwaComposerError(f"required file not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def forge() -> Path:
    mbody_root = _mbody_root()
    fetch_tool = mbody_root / "tools" / "fetch.py"
    if not fetch_tool.is_file():
        raise HakoniwaComposerError(
            "hakoniwa-mbody-registry sibling checkout was not found: "
            f"{mbody_root}"
        )

    forge_root = model_forge_root(ROBOT_ID)
    source_dir = forge_root / "source"
    build_dir = forge_root / "build"
    staging_dir = model_install_staging_dir(ROBOT_ID)
    output_dir = model_install_dir(ROBOT_ID)

    _reset_directory(source_dir)
    _reset_directory(build_dir)
    _reset_directory(staging_dir)

    print("=== Nova5 Forge: Fetch Source ===")
    _run_tool(fetch_tool, SOURCE_YAML, "--output-dir", source_dir)
    _copy_tree(source_dir, build_dir)

    entry_xacro = build_dir / "cra_description" / "urdf" / "nova5_robot.xacro"
    normalized_urdf = build_dir / "cra_description" / "urdf" / "nova5_robot.urdf"
    package_root = build_dir / "cra_description"
    mjcf_file = build_dir / "nova5.xml"
    actuator_config = RECIPE_DIR / "actuator.yaml"
    runtime_actuator_dir = RECIPE_DIR / "config" / "actuator" / "joint"
    runtime_limit_overrides = (
        RECIPE_DIR / "config" / "actuator" / "runtime-limit-overrides.yaml"
    )
    actuated_mjcf = build_dir / "nova5.actuated.xml"
    stabilized_mjcf = build_dir / "nova5.stabilized.xml"
    contact_config = RECIPE_DIR / "contact-excludes.yaml"
    contact_mjcf = build_dir / "nova5.contact.xml"

    print("\n=== Nova5 Forge: Normalize ROS Description ===")
    _run_tool(
        PACK_ROOT / "tools" / "normalize_nova5_urdf.py",
        entry_xacro,
        "--output",
        normalized_urdf,
    )

    print("\n=== Nova5 Forge: Convert URDF to MJCF ===")
    _run_tool(
        mbody_root / "tools" / "urdf2mjcf.py",
        normalized_urdf,
        "--package-root",
        f"cra_description={package_root}",
        "--output",
        mjcf_file,
    )

    if not actuator_config.is_file():
        print("\n=== Nova5 Forge: Generate Actuator Config ===")
        _run_tool(
            mbody_root / "tools" / "urdf2actuator.py",
            normalized_urdf,
            "--type",
            "position",
            "--kp",
            "1000",
            "--dampratio",
            "1.0",
            "--output",
            actuator_config,
        )

    limit_sync_args: list[object] = [
        normalized_urdf,
        "--actuator-yaml",
        actuator_config,
        "--runtime-config-dir",
        runtime_actuator_dir,
    ]
    if runtime_limit_overrides.is_file():
        limit_sync_args.extend(
            ["--runtime-limit-overrides", runtime_limit_overrides]
        )

    print("\n=== Nova5 Forge: Synchronize Joint Limits ===")
    _run_tool(
        PACK_ROOT / "tools" / "sync_arm_joint_limits.py",
        *limit_sync_args,
    )

    print("\n=== Nova5 Forge: Add Actuators ===")
    _run_tool(
        mbody_root / "tools" / "mjcf_add_actuators.py",
        mjcf_file,
        actuator_config,
        "--output",
        actuated_mjcf,
    )

    print("\n=== Nova5 Forge: Configure Simulation Options ===")
    _run_tool(
        PACK_ROOT / "tools" / "configure_mjcf_options.py",
        actuated_mjcf,
        "--timestep",
        "0.002",
        "--integrator",
        "implicitfast",
        "--output",
        stabilized_mjcf,
    )

    print("\n=== Nova5 Forge: Add Contact Excludes ===")
    _run_tool(
        mbody_root / "tools" / "mjcf_add_contact_excludes.py",
        stabilized_mjcf,
        contact_config,
        "--output",
        contact_mjcf,
    )

    _run_tool(
        PACK_ROOT / "tools" / "sync_arm_joint_limits.py",
        *limit_sync_args,
        "--validate-mjcf",
        contact_mjcf,
        "--check",
    )

    print("\n=== Nova5 Forge: Install Generated Artifacts ===")
    _copy_tree(build_dir / "cra_description", staging_dir / "cra_description")
    _copy_tree(build_dir / "nova5_moveit", staging_dir / "nova5_moveit")
    _copy_file(build_dir / "LICENSE", staging_dir / "LICENSE")
    for generated_file in (
        "nova5.xml",
        "nova5.actuated.xml",
        "nova5.stabilized.xml",
        "nova5.contact.xml",
    ):
        _copy_file(build_dir / generated_file, staging_dir / generated_file)

    published = publish_model_install(ROBOT_ID)

    print("\nNova5 forge complete.")
    print(
        "  - normalized URDF: "
        f"{output_dir / 'cra_description' / 'urdf' / 'nova5_robot.urdf'}"
    )
    print(f"  - runtime MJCF:    {output_dir / 'nova5.contact.xml'}")
    return published


def main() -> int:
    try:
        forge()
        return 0
    except subprocess.CalledProcessError as error:
        print(
            f"error: Nova5 forge tool failed with exit code {error.returncode}: "
            f"{subprocess.list2cmdline(error.cmd)}",
            file=sys.stderr,
        )
        return error.returncode or 1
    except (HakoniwaComposerError, OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
