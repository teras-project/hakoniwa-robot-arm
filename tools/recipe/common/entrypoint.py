from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from common import arm
from common.gamepad_profile import UnsupportedGamepadPlatform, resolve_dualsense_profile


GAMEPAD_PYTHON_REQUIREMENT = "pygame==2.6.1"


def _is_gamepad_configure(argv: list[str]) -> bool:
    return bool(argv) and argv[0] == "configure" and (
        "--gamepad" in argv or "--ps5-controller" in argv
    )


def _is_doctor(argv: list[str]) -> bool:
    return bool(argv) and argv[0] == "doctor"


def _gamepad_asset(launcher: dict, robot_id: str) -> dict | None:
    names = {
        f"{robot_id}-gamepad-controller",
        f"{robot_id}-ps5-controller",
    }
    return next(
        (
            item
            for item in launcher.get("assets", [])
            if isinstance(item, dict) and item.get("name") in names
        ),
        None,
    )


def _gamepad_command(launcher: dict, robot_id: str) -> str | None:
    asset = _gamepad_asset(launcher, robot_id)
    if asset is None:
        return None
    command = asset.get("command")
    if not isinstance(command, str) or not command:
        raise ValueError(f"generated Launcher gamepad command is invalid for {robot_id}")
    return command


def gamepad_dependency_error(launcher: dict, *, robot_id: str) -> str | None:
    command = _gamepad_command(launcher, robot_id)
    if command is None:
        return None
    completed = subprocess.run(
        [command, "-c", "import pygame"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if completed.returncode == 0:
        return None
    return (
        f"pygame is required for the gamepad frontend in Foundation Python: {command}. "
        "Rerun configure --gamepad from the active Hakoniwa Workspace to prepare it."
    )


def _validate_gamepad_install_target(command: str) -> None:
    if os.environ.get("HAKONIWA_WORKSPACE_ACTIVE") != "1":
        raise ValueError(
            "gamepad dependency preparation requires an active Hakoniwa Workspace"
        )

    workspace_root_value = os.environ.get("HAKONIWA_WORKSPACE_ROOT", "").strip()
    hakoniwa_home_value = os.environ.get("HAKONIWA_HOME", "").strip()
    virtual_env_value = os.environ.get("VIRTUAL_ENV", "").strip()
    if not workspace_root_value or not hakoniwa_home_value or not virtual_env_value:
        raise ValueError("active Hakoniwa Workspace environment is incomplete")

    workspace_root = Path(workspace_root_value).expanduser().resolve()
    expected_home = arm.workspace_work_dir() / "foundation/install"
    expected_venv = expected_home / "python"
    # Keep the venv executable spelling: venv/bin/python commonly points at
    # the base interpreter, so resolving the executable itself would make a
    # valid managed command appear outside the managed venv.
    expected_python = (
        Path(hakoniwa_home_value).expanduser().absolute() / "python/bin/python"
    )

    if Path(hakoniwa_home_value).expanduser().resolve() != expected_home:
        raise ValueError(
            "refusing to prepare gamepad dependency in an unexpected HAKONIWA_HOME: "
            f"{hakoniwa_home_value}"
        )
    if Path(virtual_env_value).expanduser().resolve() != expected_venv:
        raise ValueError(
            "refusing to prepare gamepad dependency in an unexpected Python environment: "
            f"{virtual_env_value}"
        )
    if Path(command).expanduser().absolute() != expected_python:
        raise ValueError(
            "refusing to prepare gamepad dependency with a non-Foundation Python: "
            f"{command}; expected={expected_python}"
        )


def prepare_gamepad_dependency(launcher: dict, *, robot_id: str) -> None:
    command = _gamepad_command(launcher, robot_id)
    if command is None:
        return
    if gamepad_dependency_error(launcher, robot_id=robot_id) is None:
        return

    _validate_gamepad_install_target(command)
    print(
        "Preparing gamepad Python dependency in Foundation Python: "
        f"{GAMEPAD_PYTHON_REQUIREMENT}"
    )
    completed = subprocess.run(
        [command, "-m", "pip", "install", GAMEPAD_PYTHON_REQUIREMENT],
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError(
            "failed to prepare gamepad Python dependency in Foundation Python: "
            f"exit={completed.returncode}"
        )

    error = gamepad_dependency_error(launcher, robot_id=robot_id)
    if error is not None:
        raise ValueError(
            "gamepad Python dependency is still unavailable after installation: "
            f"{error}"
        )
    print(f"[OK] Gamepad Python dependency: {GAMEPAD_PYTHON_REQUIREMENT}")


def inject_gamepad_device_profile(
    launcher: dict,
    *,
    robot_id: str,
    profile_path: Path,
) -> None:
    asset_name = f"{robot_id}-gamepad-controller"
    asset = next(
        (item for item in launcher.get("assets", []) if item.get("name") == asset_name),
        None,
    )
    if asset is None:
        raise ValueError(f"generated Launcher is missing gamepad asset: {asset_name}")
    args = asset.get("args")
    if not isinstance(args, list):
        raise ValueError(f"generated Launcher gamepad args are invalid: {asset_name}")
    try:
        profile_index = args.index("--device-profile") + 1
        args[profile_index] = str(profile_path)
    except (ValueError, IndexError) as error:
        raise ValueError(
            f"generated Launcher is missing --device-profile: {asset_name}"
        ) from error


def _check_doctor_gamepad_dependency(robot_id: str) -> int:
    _foundation, workspace = arm.workspace_and_foundation()
    launcher_path = workspace.recipe_config / "launcher.json"
    if not launcher_path.is_file():
        return 0
    launcher = json.loads(launcher_path.read_text(encoding="utf-8"))
    asset = _gamepad_asset(launcher, robot_id)
    if asset is None:
        return 0
    error = gamepad_dependency_error(launcher, robot_id=robot_id)
    if error is not None:
        print(f"[NG] Gamepad Python dependency: {error}")
        return 1
    print(
        "[OK] Gamepad Python dependency: pygame is importable by "
        f"{asset['command']}"
    )
    return 0


def run_arm_recipe(
    robot_id: str,
    robot_label: str,
    argv: list[str] | None = None,
) -> int:
    arm.select_robot(robot_id, robot_label)
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    gamepad_configure = _is_gamepad_configure(effective_argv)

    profile_path: Path | None = None
    if gamepad_configure:
        try:
            profile_path, profile_label = resolve_dualsense_profile(arm.arm_root())
        except UnsupportedGamepadPlatform as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
        if not profile_path.is_file():
            print(f"error: {profile_label} not found: {profile_path}", file=sys.stderr)
            return 2

    if not gamepad_configure:
        result = arm.main(effective_argv)
        if result == 0 and _is_doctor(effective_argv):
            return _check_doctor_gamepad_dependency(robot_id)
        return result

    original_write_json = arm.write_json

    def write_json_with_gamepad_contract(path: Path, data: object) -> Path:
        if path.name == "launcher.json":
            if not isinstance(data, dict):
                raise ValueError("generated Launcher data is not an object")
            prepare_gamepad_dependency(data, robot_id=robot_id)
            if profile_path is not None:
                inject_gamepad_device_profile(
                    data,
                    robot_id=robot_id,
                    profile_path=profile_path,
                )
        return original_write_json(path, data)

    arm.write_json = write_json_with_gamepad_contract
    try:
        result = arm.main(effective_argv)
        if result == 0 and profile_path is not None:
            print(f"Gamepad profile : {profile_path}")
        return result
    finally:
        arm.write_json = original_write_json


def run_arm_recipe_with_model_forge(
    robot_id: str,
    robot_label: str,
    argv: list[str] | None = None,
) -> int:
    """Expose a robot's work-owned Forge script beside the common commands."""
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    if not effective_argv or effective_argv[0] != "forge":
        if effective_argv in (["-h"], ["--help"]):
            print(f"{robot_label} additional command: forge")
        return run_arm_recipe(robot_id, robot_label, effective_argv)

    parser = argparse.ArgumentParser(
        prog=f"{Path(sys.argv[0]).name} forge",
        description=(
            f"Regenerate the {robot_label} model using the active Hakoniwa "
            "Composer workspace."
        ),
    )
    parser.parse_args(effective_argv[1:])

    try:
        from _hakoniwa_composer import composer_root, model_install_dir

        composer = composer_root()
        if os.environ.get("HAKONIWA_WORKSPACE_ACTIVE") != "1":
            raise ValueError(
                f"{robot_label} forge requires an active Hakoniwa Composer workspace"
            )
        active_value = os.environ.get("HAKONIWA_WORKSPACE_ROOT", "").strip()
        if not active_value:
            raise ValueError(
                "HAKONIWA_WORKSPACE_ACTIVE=1 requires HAKONIWA_WORKSPACE_ROOT"
            )
        active = Path(active_value).expanduser().resolve()
        if active != composer:
            raise ValueError(
                "active Hakoniwa workspace does not match Hakoniwa Composer: "
                f"active={active}, composer={composer}"
            )

        recipe_file = (
            arm.arm_root() / "recipes" / robot_id / f"{robot_id}-model-forge.yaml"
        )
        script = arm.arm_root() / "recipes" / robot_id / f"forge-{robot_id}.sh"
        for path, label in ((recipe_file, "Model Forge Recipe"), (script, "Forge script")):
            if not path.is_file():
                raise ValueError(f"{robot_label} {label} not found: {path}")

        doctor = [
            sys.executable,
            str(composer / "tools/recipe.py"),
            "doctor",
            "--recipe",
            str(recipe_file),
        ]
        print("+", subprocess.list2cmdline(doctor), flush=True)
        if subprocess.run(doctor, cwd=composer, check=False).returncode != 0:
            raise ValueError(
                f"{robot_label} Model Forge Recipe is not ready; run: "
                f"python tools/recipe.py configure --recipe {recipe_file}"
            )

        env = os.environ.copy()
        env["PYTHON_CMD"] = sys.executable
        command = ["bash", str(script)]
        print(f"Composer         : {composer}")
        print(f"Forge Python     : {sys.executable}")
        print(f"{robot_label} output : {model_install_dir(robot_id)}")
        print("+", subprocess.list2cmdline(command), flush=True)
        return subprocess.run(
            command,
            cwd=arm.arm_root(),
            env=env,
            check=False,
        ).returncode
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
