from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch


RECIPE_DIR = Path(__file__).resolve().parents[1] / "recipe"
sys.path.insert(0, str(RECIPE_DIR))

import ros2_workspace  # noqa: E402


class PduRosSourceTest(unittest.TestCase):
    def test_new_checkout_uses_recorded_compatible_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hakoniwa-pdu-ros"

            def clone_and_checkout(argv, **kwargs):
                if "clone" in argv:
                    path.mkdir()
                    (path / "package.xml").touch()

            with (
                patch.object(ros2_workspace, "run", side_effect=clone_and_checkout) as run,
                patch.object(ros2_workspace.subprocess, "run", return_value=SimpleNamespace(returncode=0)),
            ):
                ros2_workspace.ensure_source(path, "hakoniwa-pdu-ros")

            revision = json.loads((ros2_workspace.ARM_ROOT / "tools/dobot/versions.json").read_text())["hakoniwa-pdu-ros"]
            self.assertEqual(run.call_args_list[1], call(
                ["git", "-C", path, "checkout", "--detach", revision]))

    def test_existing_checkout_without_fix_is_rejected_without_switching_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "hakoniwa-pdu-ros"
            path.mkdir()
            (path / "package.xml").touch()
            with (
                patch.object(ros2_workspace, "run") as run,
                patch.object(ros2_workspace.subprocess, "run", return_value=SimpleNamespace(returncode=1)),
            ):
                with self.assertRaisesRegex(ValueError, "fetch the fix or select a compatible"):
                    ros2_workspace.ensure_source(path, "hakoniwa-pdu-ros")
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
