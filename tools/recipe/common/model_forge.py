from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2]
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from _hakoniwa_composer import composer_root, model_install_dir  # noqa: E402
from common import arm  # noqa: E402
from common.entrypoint import run_arm_recipe  # noqa: E402


def run_arm_recipe_with_python_model_forge(
    robot_id: str,
    robot_label: str,
    argv: list[str] | None = None,
) -> int:
    """Expose a robot-owned Python Forge beside the common arm commands."""
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
        forge_script = arm.arm_root() / "recipes" / robot_id / "forge.py"
        for path, label in (
            (recipe_file, "Model Forge Recipe"),
            (forge_script, "Python Forge implementation"),
        ):
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

        command = [sys.executable, str(forge_script)]
        print(f"Composer         : {composer}")
        print(f"Forge Python     : {sys.executable}")
        print(f"{robot_label} output : {model_install_dir(robot_id)}")
        print("+", subprocess.list2cmdline(command), flush=True)
        return subprocess.run(
            command,
            cwd=arm.arm_root(),
            check=False,
        ).returncode
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
