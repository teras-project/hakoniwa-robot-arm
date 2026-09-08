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
    HakoniwaComposerError,
    arm_root,
    composer_root,
    load_foundation_module,
    model_install_dir,
)
from common.entrypoint import run_arm_recipe  # noqa: E402


FORGE_RECIPE_ID = "nova5-model-forge"
FORGE_REQUIRED_MODULES = ("yaml",)


def _require_active_workspace() -> Path:
    root = composer_root()
    if os.environ.get("HAKONIWA_WORKSPACE_ACTIVE") != "1":
        raise HakoniwaComposerError(
            "Nova5 forge requires an active Hakoniwa Composer workspace"
        )
    configured = os.environ.get("HAKONIWA_WORKSPACE_ROOT", "").strip()
    if not configured:
        raise HakoniwaComposerError(
            "HAKONIWA_WORKSPACE_ACTIVE=1 requires HAKONIWA_WORKSPACE_ROOT"
        )
    active = Path(configured).expanduser().resolve()
    if active != root:
        raise HakoniwaComposerError(
            "active Hakoniwa workspace does not match Hakoniwa Composer: "
            f"active={active}, composer={root}"
        )
    return root


def _forge_recipe_file() -> Path:
    return arm_root() / "recipes/nova5/nova5-model-forge.yaml"


def _forge_python() -> Path:
    foundation = load_foundation_module()
    workspace = foundation.resolve_workspace(arm_root(), FORGE_RECIPE_ID)
    # Do not resolve this path: a venv's bin/python is commonly a symlink to the
    # base interpreter, and resolving it would escape the Composer-managed
    # Python environment when invoking pip or the forge tools.
    python = Path(
        foundation.foundation_python_executable(workspace.foundation_python)
    ).absolute()
    if not python.is_file():
        raise HakoniwaComposerError(
            "Composer-managed Python was not found; complete setup.md first: "
            f"{python}"
        )
    return python


def _mbody_root() -> Path:
    configured = os.environ.get("HAKONIWA_MBODY_REGISTRY_ROOT", "").strip()
    return (
        Path(configured).expanduser().resolve()
        if configured
        else (arm_root().parent / "hakoniwa-mbody-registry").resolve()
    )


def _mujoco_root() -> Path:
    configured = os.environ.get("HAKONIWA_MUJOCO_ROBOTS_ROOT", "").strip()
    return (
        Path(configured).expanduser().resolve()
        if configured
        else (arm_root().parent / "hakoniwa-mujoco-robots").resolve()
    )


def _expected_mujoco_version(mujoco_root: Path) -> str:
    version_file = mujoco_root / "MUJOCO_VERSION.txt"
    if not version_file.is_file():
        raise HakoniwaComposerError(
            "MuJoCo version definition was not found in hakoniwa-mujoco-robots: "
            f"{version_file}"
        )
    version = version_file.read_text(encoding="utf-8").strip()
    if not version:
        raise HakoniwaComposerError(f"MuJoCo version definition is empty: {version_file}")
    return version


def _configure_hint(composer_root_path: Path, recipe_file: Path) -> str:
    relative = os.path.relpath(recipe_file, composer_root_path)
    return f"python tools/recipe.py configure --recipe {relative}"


def _check_recipe_ready(
    composer_root_path: Path,
    python: Path,
    recipe_file: Path,
) -> None:
    command = [
        str(python),
        str(composer_root_path / "tools/recipe.py"),
        "doctor",
        "--recipe",
        str(recipe_file),
    ]
    print("+", subprocess.list2cmdline(command), flush=True)
    completed = subprocess.run(command, cwd=composer_root_path, check=False)
    if completed.returncode != 0:
        raise HakoniwaComposerError(
            "Nova5 model-forge Recipe is not ready; run: "
            + _configure_hint(composer_root_path, recipe_file)
        )


def _installed_python_package_version(python: Path, package: str) -> str | None:
    probe = (
        "from importlib.metadata import PackageNotFoundError, version; "
        f"name={package!r}; "
        "\ntry:\n print(version(name))\n"
        "except PackageNotFoundError:\n raise SystemExit(1)\n"
    )
    completed = subprocess.run(
        [str(python), "-c", probe],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def _check_forge_python_dependencies(
    composer_root_path: Path,
    python: Path,
    recipe_file: Path,
    expected_mujoco_version: str,
) -> None:
    missing: list[str] = []
    for module in FORGE_REQUIRED_MODULES:
        completed = subprocess.run(
            [str(python), "-c", f"import {module}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if completed.returncode != 0:
            missing.append(module)
    if missing:
        raise HakoniwaComposerError(
            "Nova5 forge Python dependencies are missing from Composer Python "
            f"({', '.join(missing)}); rerun: "
            + _configure_hint(composer_root_path, recipe_file)
        )

    installed_mujoco = _installed_python_package_version(python, "mujoco")
    if installed_mujoco != expected_mujoco_version:
        raise HakoniwaComposerError(
            "Composer Python MuJoCo version does not match "
            "hakoniwa-mujoco-robots/MUJOCO_VERSION.txt: "
            f"expected={expected_mujoco_version}, installed={installed_mujoco or 'missing'}; "
            "rerun: "
            + _configure_hint(composer_root_path, recipe_file)
        )


def forge() -> int:
    composer_root_path = _require_active_workspace()
    recipe_file = _forge_recipe_file()
    python = _forge_python()

    _check_recipe_ready(composer_root_path, python, recipe_file)

    mbody_root = _mbody_root()
    mujoco_root = _mujoco_root()
    mujoco_version = _expected_mujoco_version(mujoco_root)
    _check_forge_python_dependencies(
        composer_root_path,
        python,
        recipe_file,
        mujoco_version,
    )

    required_tools = (
        "tools/fetch.py",
        "tools/path_utils.py",
        "tools/urdf2mjcf.py",
        "tools/urdf2actuator.py",
        "tools/mjcf_add_actuators.py",
        "tools/mjcf_add_contact_excludes.py",
    )
    missing_tools = [
        relative for relative in required_tools if not (mbody_root / relative).is_file()
    ]
    if missing_tools:
        raise HakoniwaComposerError(
            "hakoniwa-mbody-registry is incomplete at "
            f"{mbody_root}; missing={', '.join(missing_tools)}"
        )

    forge_script = arm_root() / "recipes/nova5/forge-nova5.sh"
    if not forge_script.is_file():
        raise HakoniwaComposerError(f"Nova5 forge script not found: {forge_script}")

    output_dir = model_install_dir("nova5")
    env = os.environ.copy()
    env["PYTHON_CMD"] = str(python)
    env["HAKONIWA_MBODY_REGISTRY_ROOT"] = str(mbody_root)

    command = ["bash", str(forge_script)]
    print(f"Composer         : {composer_root_path}")
    print(f"Forge Python     : {python}")
    print(f"MBody Registry   : {mbody_root}")
    print(f"MuJoCo Robots    : {mujoco_root}")
    print(f"MuJoCo version   : {mujoco_version}")
    print(f"Nova5 output     : {output_dir}")
    print("+", subprocess.list2cmdline(command), flush=True)
    return subprocess.run(command, cwd=arm_root(), env=env, check=False).returncode


def _forge_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog=f"{Path(sys.argv[0]).name} forge",
        description=(
            "Regenerate the Nova5 MuJoCo model using the active Hakoniwa "
            "Composer workspace."
        ),
    )


def main(argv: list[str] | None = None) -> int:
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    if effective_argv and effective_argv[0] == "forge":
        _forge_parser().parse_args(effective_argv[1:])
        try:
            return forge()
        except (HakoniwaComposerError, OSError, RuntimeError, ValueError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 2

    if effective_argv in (["-h"], ["--help"]):
        print("Nova5 additional command: forge")
    return run_arm_recipe("nova5", "Nova5", effective_argv)


if __name__ == "__main__":
    raise SystemExit(main())
