#!/usr/bin/env python3
"""Install the pinned excavator bucket-proxy tools cross-platform."""

from __future__ import annotations

import subprocess
import sys
import venv
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from _hakoniwa_composer import (  # noqa: E402
    excavator_bucket_proxy_python,
    model_forge_root,
)


def install() -> Path:
    pack_root = TOOLS_DIR.parent
    environment = model_forge_root("excavator") / "tools-venv"
    python = excavator_bucket_proxy_python()
    requirements = pack_root / "recipes/excavator/bucket-proxy-requirements.txt"
    if not python.is_file():
        environment.parent.mkdir(parents=True, exist_ok=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    subprocess.run(
        [str(python), "-m", "pip", "install", "--requirement", str(requirements)],
        check=True,
    )
    subprocess.run(
        [
            str(python),
            "-c",
            "import mujoco, mujoco.viewer, numpy, trimesh, yaml; "
            "print('Excavator bucket-proxy tools are ready.')",
        ],
        check=True,
    )
    return python


def main() -> int:
    try:
        install()
        return 0
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
