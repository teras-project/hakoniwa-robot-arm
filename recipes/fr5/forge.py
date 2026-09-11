#!/usr/bin/env python3
"""Forge the FR5 runtime model without a shell dependency."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

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

ROBOT_ID = "fr5"
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


def _forge_paths() -> tuple[Path, Path]:
    config = yaml.safe_load(SOURCE_YAML.read_text(encoding="utf-8"))
    forge_config = config.get("forge", {}) if isinstance(config, dict) else {}
    entry = forge_config.get("entry_urdf", "")
    normalized = forge_config.get("normalized_urdf", "")
    if not isinstance(entry, str) or not entry:
        raise HakoniwaComposerError(
            f"forge.entry_urdf is not defined in {SOURCE_YAML}"
        )
    if not isinstance(normalized, str) or not normalized:
        raise HakoniwaComposerError(
            f"forge.normalized_urdf is not defined in {SOURCE_YAML}"
        )
    return Path(entry), Path(normalized)


def _validate_urdf_links(path: Path) -> list[str]:
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as error:
        return [f"failed to parse URDF {path}: {error}"]

    links = {
        link.get("name")
        for link in root.findall("link")
        if link.get("name")
    }
    invalid: list[str] = []
    for joint in root.findall("joint"):
        joint_name = joint.get("name", "<unnamed>")
        for relation in ("parent", "child"):
            element = joint.find(relation)
            link_name = element.get("link") if element is not None else None
            if not link_name:
                invalid.append(f"joint '{joint_name}' has no {relation} link")
            elif link_name not in links:
                invalid.append(
                    f"joint '{joint_name}' {relation} references undefined link "
                    f"'{link_name}'"
                )
    return invalid


def _require_valid_urdf(path: Path, guidance: str) -> None:
    invalid = _validate_urdf_links(path)
    if invalid:
        details = "\n".join(f"  - {message}" for message in invalid)
        raise HakoniwaComposerError(f"{guidance}\n{details}")


def forge() -> Path:
    mbody_root = _mbody_root()
    fetch_tool = mbody_root / "tools" / "fetch.py"
    if not fetch_tool.is_file():
        raise HakoniwaComposerError(
            "hakoniwa-mbody-registry sibling checkout was not found: "
            f"{mbody_root}"
        )

    entry_rel, normalized_rel = _forge_paths()
    forge_root = model_forge_root(ROBOT_ID)
    source_dir = forge_root / "source"
    normalized_dir = forge_root / "normalized"
    build_dir = forge_root / "build"
    staging_dir = model_install_staging_dir(ROBOT_ID)
    output_dir = model_install_dir(ROBOT_ID)

    source_dir.mkdir(parents=True, exist_ok=True)
    normalized_dir.mkdir(parents=True, exist_ok=True)
    _reset_directory(build_dir)
    _reset_directory(staging_dir)

    source_urdf = source_dir / entry_rel
    normalized_urdf = normalized_dir / normalized_rel
    entry_urdf = build_dir / normalized_rel

    print("=== FR5 Forge: Fetch Source ===")
    print(f"  - Pack root:   {PACK_ROOT}")
    print(f"  - Source YAML: {SOURCE_YAML}")
    print(f"  - Output dir:  {output_dir}")
    if not source_urdf.is_file():
        _run_tool(fetch_tool, SOURCE_YAML, "--output-dir", source_dir)
    else:
        print("Using retained FR5 source:")
        print(f"  {source_urdf}")
    if not source_urdf.is_file():
        raise HakoniwaComposerError(
            f"Source URDF not found after fetch: {source_urdf}"
        )

    guidance = f"Follow: {PACK_ROOT / 'sources/models/fr5/README.md'}"
    if not normalized_urdf.is_file():
        print("\n=== FR5 Forge: Validate Upstream URDF ===")
        invalid = _validate_urdf_links(source_urdf)
        if invalid:
            details = "\n".join(f"  - {message}" for message in invalid)
            raise HakoniwaComposerError(
                "FR5 source normalization is required before conversion.\n"
                "Keep the fetched original unchanged and create the corrected URDF at:\n"
                f"  {normalized_urdf}\n{guidance}\n{details}"
            )
        _copy_file(source_urdf, normalized_urdf)

    print("\n=== FR5 Forge: Validate Normalized URDF ===")
    print(f"  - Original:   {source_urdf}")
    print(f"  - Normalized: {normalized_urdf}")
    _require_valid_urdf(
        normalized_urdf,
        f"Correct the normalized URDF and rerun this Forge command.\n{guidance}",
    )

    _copy_tree(source_dir, build_dir)
    _copy_file(normalized_urdf, entry_urdf)
    print("FR5 normalized URDF is ready for conversion.")

    obj_urdf = entry_urdf.with_name(f"{entry_urdf.stem}.obj.urdf")
    print("\n=== FR5 Forge: Convert DAE to OBJ ===")
    print(f"  - Input URDF:  {entry_urdf}")
    print(f"  - Output URDF: {obj_urdf}")
    _run_tool(
        mbody_root / "tools" / "urdf_dae2obj.py",
        entry_urdf,
        "--output",
        obj_urdf,
    )
    if not obj_urdf.is_file():
        raise HakoniwaComposerError(f"OBJ-converted URDF not found: {obj_urdf}")

    mjcf_file = build_dir / "FR5WM.xml"
    print("\n=== FR5 Forge: Convert URDF to MJCF ===")
    _run_tool(
        mbody_root / "tools" / "urdf2mjcf.py",
        obj_urdf,
        "--output",
        mjcf_file,
    )
    if not mjcf_file.is_file():
        raise HakoniwaComposerError(f"MJCF file not found: {mjcf_file}")

    actuator_config = RECIPE_DIR / "actuator.yaml"
    runtime_actuator_dir = RECIPE_DIR / "config" / "actuator" / "joint"
    runtime_limit_overrides = (
        RECIPE_DIR / "config" / "actuator" / "runtime-limit-overrides.yaml"
    )
    if not actuator_config.is_file():
        print("\n=== FR5 Forge: Generate Actuator Config ===")
        _run_tool(
            mbody_root / "tools" / "urdf2actuator.py",
            entry_urdf,
            "--type",
            "position",
            "--kp",
            "100",
            "--dampratio",
            "1.0",
            "--output",
            actuator_config,
        )
        if not actuator_config.is_file():
            raise HakoniwaComposerError(
                f"Actuator config not found: {actuator_config}"
            )
    else:
        print("\n=== FR5 Forge: Actuator Config Already Exists ===")
        print(f"  - Actuator config: {actuator_config}")

    limit_sync_args: list[object] = [
        obj_urdf,
        "--actuator-yaml",
        actuator_config,
        "--runtime-config-dir",
        runtime_actuator_dir,
    ]
    if runtime_limit_overrides.is_file():
        limit_sync_args.extend(
            ["--runtime-limit-overrides", runtime_limit_overrides]
        )

    print("\n=== FR5 Forge: Synchronize Joint Limits ===")
    _run_tool(PACK_ROOT / "tools" / "sync_arm_joint_limits.py", *limit_sync_args)

    actuated_mjcf = build_dir / "FR5WM.actuated.xml"
    print("\n=== FR5 Forge: Add Actuators to MJCF ===")
    _run_tool(
        mbody_root / "tools" / "mjcf_add_actuators.py",
        mjcf_file,
        actuator_config,
        "--output",
        actuated_mjcf,
    )
    if not actuated_mjcf.is_file():
        raise HakoniwaComposerError(f"Actuated MJCF not found: {actuated_mjcf}")

    contact_config = RECIPE_DIR / "contact-excludes.yaml"
    contact_mjcf = build_dir / "FR5WM.contact.xml"
    print("\n=== FR5 Forge: Add Contact Excludes ===")
    _run_tool(
        mbody_root / "tools" / "mjcf_add_contact_excludes.py",
        actuated_mjcf,
        contact_config,
        "--output",
        contact_mjcf,
    )
    if not contact_mjcf.is_file():
        raise HakoniwaComposerError(
            f"Contact-adjusted MJCF not found: {contact_mjcf}"
        )
    _run_tool(
        PACK_ROOT / "tools" / "sync_arm_joint_limits.py",
        *limit_sync_args,
        "--validate-mjcf",
        contact_mjcf,
        "--check",
    )

    print("\n=== FR5 Forge: Install Generated Artifacts ===")
    _copy_tree(build_dir, staging_dir)
    published = publish_model_install(ROBOT_ID)
    print(f"  - runtime MJCF: {output_dir / 'FR5WM.contact.xml'}")
    return published


def main() -> int:
    try:
        forge()
        return 0
    except subprocess.CalledProcessError as error:
        print(
            f"error: FR5 forge tool failed with exit code {error.returncode}: "
            f"{subprocess.list2cmdline(error.cmd)}",
            file=sys.stderr,
        )
        return error.returncode or 1
    except (HakoniwaComposerError, OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
