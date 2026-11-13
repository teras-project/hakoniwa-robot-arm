from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


RECIPE_DIR = Path(__file__).resolve().parents[1] / "recipe"
sys.path.insert(0, str(RECIPE_DIR))

from common import arm  # noqa: E402


class StandaloneBuildTest(unittest.TestCase):
    def test_build_ignores_stale_dobot_cache_without_generated_types(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "CMakeLists.txt").write_text(
                "cmake_minimum_required(VERSION 3.21)\n"
                "project(stale_dobot_cache NONE)\n"
                "option(HAKO_ARM_ENABLE_DOBOT \"Dobot backend\" OFF)\n"
                "if(HAKO_ARM_ENABLE_DOBOT)\n"
                "  message(FATAL_ERROR \"Dobot types missing\")\n"
                "endif()\n"
                "add_custom_target(robot-arm-hakoniwa-asset)\n"
            )
            (root / "src").mkdir()
            (root / "src/CMakeLists.txt").touch()
            build_dir = root / "build"
            failed = subprocess.run(
                ["cmake", "-S", str(root), "-B", str(build_dir), "-DHAKO_ARM_ENABLE_DOBOT=ON"],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(failed.returncode, 0)
            workspace = SimpleNamespace(recipe_root=root, install_prefix=root / "foundation")
            consumer = SimpleNamespace(cmake_consumer_args=lambda _: [])
            with (
                patch.object(arm, "workspace_and_foundation", return_value=(object(), workspace)),
                patch.object(arm, "load_foundation_consumer_module", return_value=consumer),
                patch.object(arm, "arm_root", return_value=root),
                patch.object(arm, "environment", return_value=os.environ.copy()),
            ):
                self.assertEqual(arm.build(root, headless=True), 0)
            self.assertIn(
                "HAKO_ARM_ENABLE_DOBOT:BOOL=OFF",
                (build_dir / "CMakeCache.txt").read_text(),
            )


if __name__ == "__main__":
    unittest.main()
