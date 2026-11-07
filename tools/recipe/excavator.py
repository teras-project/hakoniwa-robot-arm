#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from _hakoniwa_composer import (  # noqa: E402
    HakoniwaComposerError, arm_root, composer_root,
    excavator_bucket_proxy_python, load_foundation_module, model_install_dir,
)
from common.entrypoint import run_arm_recipe  # noqa: E402

FORGE_RECIPE_ID = "excavator-model-forge"


def _require_active_workspace() -> Path:
    root = composer_root()
    configured = os.environ.get("HAKONIWA_WORKSPACE_ROOT", "").strip()
    if os.environ.get("HAKONIWA_WORKSPACE_ACTIVE") != "1" or not configured:
        raise HakoniwaComposerError("Excavator forge requires an active Hakoniwa Composer workspace")
    if Path(configured).expanduser().resolve() != root:
        raise HakoniwaComposerError("active Hakoniwa workspace does not match Hakoniwa Composer")
    return root


def _forge_python() -> Path:
    foundation = load_foundation_module()
    workspace = foundation.resolve_workspace(arm_root(), FORGE_RECIPE_ID)
    python = Path(foundation.foundation_python_executable(workspace.foundation_python)).absolute()
    if not python.is_file():
        raise HakoniwaComposerError(f"Composer-managed Python was not found; complete setup first: {python}")
    return python


def _mbody_root() -> Path:
    configured = os.environ.get("HAKONIWA_MBODY_REGISTRY_ROOT", "").strip()
    return (Path(configured).expanduser().resolve() if configured else (arm_root().parent / "hakoniwa-mbody-registry").resolve())


def forge() -> int:
    composer = _require_active_workspace()
    recipe = arm_root() / "recipes/excavator/excavator-model-forge.yaml"
    python = _forge_python()
    doctor = [str(python), str(composer / "tools/recipe.py"), "doctor", "--recipe", str(recipe)]
    print("+", subprocess.list2cmdline(doctor), flush=True)
    if subprocess.run(doctor, cwd=composer, check=False).returncode:
        raise HakoniwaComposerError(
            "Excavator model-forge Recipe is not ready; run: python tools/recipe.py configure --recipe "
            + os.path.relpath(recipe, composer)
        )
    mbody = _mbody_root()
    required = ("tools/fetch.py", "tools/path_utils.py", "tools/urdf2mjcf.py", "tools/mjcf_add_actuators.py", "tools/mjcf_add_contact_excludes.py")
    missing = [name for name in required if not (mbody / name).is_file()]
    if missing:
        raise HakoniwaComposerError(f"hakoniwa-mbody-registry is incomplete at {mbody}; missing={', '.join(missing)}")
    bucket_python = excavator_bucket_proxy_python()
    if not bucket_python.is_file():
        raise HakoniwaComposerError("Recipe-owned bucket proxy Python is missing; run: python tools/install_excavator_bucket_proxy_tools.py")
    program = arm_root() / "recipes/excavator/forge.py"
    command = [str(python), str(program)]
    env = os.environ.copy()
    env["HAKONIWA_MBODY_REGISTRY_ROOT"] = str(mbody)
    print(f"Composer         : {composer}")
    print(f"Forge Python     : {python}")
    print(f"Bucket Python    : {bucket_python}")
    print(f"MBody Registry   : {mbody}")
    print(f"Excavator output : {model_install_dir('excavator')}")
    print("+", subprocess.list2cmdline(command), flush=True)
    return subprocess.run(command, cwd=arm_root(), env=env, check=False).returncode


def validate_bucket() -> int:
    python = excavator_bucket_proxy_python()
    if not python.is_file():
        raise HakoniwaComposerError("Recipe-owned bucket proxy Python is missing; run: python tools/install_excavator_bucket_proxy_tools.py")
    command = [
        str(python), str(arm_root() / "tools/validate_excavator_bucket_collision.py"),
        str(model_install_dir("excavator") / "excavator.soil.xml"),
        "--config", str(arm_root() / "recipes/excavator/bucket-collision.yaml"),
    ]
    print("+", subprocess.list2cmdline(command), flush=True)
    return subprocess.run(command, cwd=arm_root(), check=False).returncode


def main(argv: list[str] | None = None) -> int:
    effective = list(sys.argv[1:] if argv is None else argv)
    if effective and effective[0] == "forge":
        argparse.ArgumentParser(prog=f"{Path(sys.argv[0]).name} forge").parse_args(effective[1:])
        try:
            return forge()
        except (HakoniwaComposerError, OSError, RuntimeError, ValueError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
    if effective and effective[0] == "validate-bucket":
        argparse.ArgumentParser(prog=f"{Path(sys.argv[0]).name} validate-bucket").parse_args(effective[1:])
        try:
            return validate_bucket()
        except (HakoniwaComposerError, OSError, RuntimeError, ValueError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
    if effective in (["-h"], ["--help"]):
        print("Excavator additional commands: forge, validate-bucket")
    return run_arm_recipe("excavator", "MathScavator9000 Excavator", effective)


if __name__ == "__main__":
    raise SystemExit(main())
