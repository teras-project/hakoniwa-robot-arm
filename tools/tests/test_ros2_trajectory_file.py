from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "ros2_packages"
    / "hakoniwa_arm_samples"
)
sys.path.insert(0, str(PACKAGE_ROOT))

from hakoniwa_arm_samples.trajectory_file import load_trajectory_file


class Ros2TrajectoryFileTest(unittest.TestCase):
    def write_payload(self, root: Path, payload: object) -> Path:
        path = root / "trajectory.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_loads_the_standalone_trajectory_format(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write_payload(
                Path(temporary),
                {
                    "joint_names": ["joint1", "joint2"],
                    "points": [
                        {"time_from_start": 0.0, "positions": [0.0, 0.0]},
                        {"time_from_start": 1.5, "positions": [0.2, -0.3]},
                    ],
                },
            )

            joint_names, points = load_trajectory_file(path)

            self.assertEqual(joint_names, ["joint1", "joint2"])
            self.assertEqual(
                points,
                [
                    {"time_from_start": 0.0, "positions": [0.0, 0.0]},
                    {"time_from_start": 1.5, "positions": [0.2, -0.3]},
                ],
            )

    def test_rejects_a_position_count_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write_payload(
                Path(temporary),
                {
                    "joint_names": ["joint1", "joint2"],
                    "points": [
                        {"time_from_start": 0.0, "positions": [0.0]},
                    ],
                },
            )

            with self.assertRaisesRegex(ValueError, "must contain 2 values"):
                load_trajectory_file(path)

    def test_rejects_non_increasing_times(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = self.write_payload(
                Path(temporary),
                {
                    "joint_names": ["joint1"],
                    "points": [
                        {"time_from_start": 1.0, "positions": [0.0]},
                        {"time_from_start": 1.0, "positions": [0.1]},
                    ],
                },
            )

            with self.assertRaisesRegex(ValueError, "strictly increasing"):
                load_trajectory_file(path)


if __name__ == "__main__":
    unittest.main()
