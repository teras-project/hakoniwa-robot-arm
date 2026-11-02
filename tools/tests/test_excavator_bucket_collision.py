from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from _hakoniwa_composer import excavator_bucket_proxy_python  # noqa: E402
WORK_DIR = Path(os.environ.get("HAKONIWA_WORK_DIR", ROOT.parent / "hakoniwa-business-pack/work"))
FORGE_ROOT = WORK_DIR / "model-forge/excavator"
FORGED_MODEL_AVAILABLE = (FORGE_ROOT / "install/excavator.soil.xml").is_file()


def tools_python() -> Path:
    candidates = (
        excavator_bucket_proxy_python(),
        ROOT.parent / "hakoniwa-mbody-registry/.venv/bin/python",
        ROOT.parent / "hakoniwa-business-pack/work/foundation/install/python/bin/python",
    )
    for candidate in candidates:
        if candidate.is_file():
            probe = subprocess.run(
                [str(candidate), "-c", "import yaml"], capture_output=True, check=False
            )
            if probe.returncode == 0:
                return candidate
    raise RuntimeError(
        "bucket proxy Python is unavailable; run "
        "python tools/install_excavator_bucket_proxy_tools.py"
    )


MINIMAL_MJCF = """\
<mujoco model="bucket-test">
  <asset><mesh name="bucket_mesh" file="unused.stl"/></asset>
  <worldbody>
    <body name="stick_bucket_link">
      <geom name="bucket_visual" type="mesh" mesh="bucket_mesh" group="1" density="0" rgba="1 1 0 1" contype="0" conaffinity="0"/>
      <geom name="bucket_source_collision" type="mesh" mesh="bucket_mesh" group="3" rgba="1 1 0 0" contype="1" conaffinity="1"/>
    </body>
  </worldbody>
</mujoco>
"""


def config_text(frame_rpy=(0, 0, 90), floor_rpy=(90, 0, 0)) -> str:
    parts = []
    for name in ("floor", "back", "side_left", "side_right", "cutting_edge"):
        center = "[1.0, 0.0, 0.0]" if name == "floor" else "[0.0, 0.0, 0.0]"
        rpy = f"[{floor_rpy[0]}, {floor_rpy[1]}, {floor_rpy[2]}]" if name == "floor" else "[0, 0, 0]"
        parts.append(
            f"""  {name}:
    enabled: true
    type: box
    description: synthetic {name}
    center_m: {center}
    dimensions_m: [1.0, 2.0, 0.1]
    rpy_deg: {rpy}
    rgba: [0.1, 0.2, 0.3, 0.5]
"""
        )
    return f"""\
version: 1
calibration: {{status: unverified, note: synthetic unit test}}
frame:
  parent: stick_bucket_link
  description: synthetic parent frame
  origin_in_parent_m: [1.0, 2.0, 3.0]
  rpy_deg: [{frame_rpy[0]}, {frame_rpy[1]}, {frame_rpy[2]}]
defaults:
  contype: 1
  conaffinity: 1
  condim: 4
  friction: [1.0, 0.02, 0.001]
  density: 0
  group: 0
parts:
{"".join(parts)}debug:
  enabled: true
  visual_mesh_alpha: 0.3
  show_proxy_frame: true
  show_part_labels: true
  show_collision_parts: true
  show_parent_frame: true
"""


class ExcavatorBucketCollisionTest(unittest.TestCase):
    def test_recipe_owns_the_pinned_tool_environment(self):
        requirements = (
            ROOT / "recipes/excavator/bucket-proxy-requirements.txt"
        ).read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            requirements,
            [
                "PyYAML==6.0.3",
                "mujoco==3.10.0",
                "numpy==2.5.1",
                "trimesh==4.12.2",
            ],
        )
        forge_recipe = (
            ROOT / "recipes/excavator/excavator-model-forge.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("bucket-proxy-requirements.txt", forge_recipe)
        self.assertIn("install_excavator_bucket_proxy_tools.py", forge_recipe)
        recipe_cli = (ROOT / "tools/recipe/common/arm.py").read_text(encoding="utf-8")
        self.assertNotIn("launch_passive", recipe_cli)

    def generate(self, directory: Path, config_payload: str):
        source = directory / "source.xml"
        config = directory / "bucket-collision.yaml"
        output = directory / "bucket.xml"
        debug = directory / "debug.xml"
        source.write_text(MINIMAL_MJCF, encoding="utf-8")
        config.write_text(config_payload, encoding="utf-8")
        result = subprocess.run(
            [
                str(tools_python()),
                str(ROOT / "tools/generate_excavator_bucket_collision.py"),
                str(source),
                "--config", str(config),
                "--output", str(output),
                "--debug-output", str(debug),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        return result, output, debug, config

    def test_full_dimensions_degrees_and_frame_transform(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, output, _, _ = self.generate(Path(temporary), config_text())
            self.assertEqual(result.returncode, 0, result.stderr)
            root = ET.parse(output).getroot()
            floor = root.find(".//geom[@name='bucket_proxy_floor']")
            self.assertEqual(
                [float(value) for value in floor.get("size").split()],
                [0.5, 1.0, 0.05],
            )
            self.assertEqual(
                [float(value) for value in floor.get("pos").split()],
                [1.0, 3.0, 3.0],
            )
            quaternion = [float(value) for value in floor.get("quat").split()]
            for actual, expected in zip(quaternion, [0.5, 0.5, 0.5, 0.5]):
                self.assertAlmostEqual(actual, expected, places=10)
            self.assertIsNone(floor.get("euler"))

    def test_ninety_degrees_is_not_interpreted_as_radians(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, output, _, _ = self.generate(
                Path(temporary), config_text(frame_rpy=(0, 0, 0))
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            floor = ET.parse(output).getroot().find(
                ".//geom[@name='bucket_proxy_floor']"
            )
            quaternion = [float(value) for value in floor.get("quat").split()]
            expected = math.sqrt(0.5)
            self.assertAlmostEqual(quaternion[0], expected, places=10)
            self.assertAlmostEqual(quaternion[1], expected, places=10)
            self.assertAlmostEqual(quaternion[2], 0.0, places=10)
            self.assertAlmostEqual(quaternion[3], 0.0, places=10)

    def test_open_five_part_structure_and_debug_frame(self):
        with tempfile.TemporaryDirectory() as temporary:
            result, output, debug, _ = self.generate(Path(temporary), config_text())
            self.assertEqual(result.returncode, 0, result.stderr)
            root = ET.parse(output).getroot()
            parent = root.find(".//body[@name='stick_bucket_link']")
            names = {
                geom.get("name")
                for geom in parent.findall("geom")
                if (geom.get("name") or "").startswith("bucket_proxy_")
            }
            self.assertEqual(
                names,
                {f"bucket_proxy_{name}" for name in ("floor", "back", "side_left", "side_right", "cutting_edge")},
            )
            self.assertNotIn("bucket_proxy_front", names)
            self.assertNotIn("bucket_proxy_ceiling", names)
            self.assertTrue(
                all(geom.get("contype") == "0" for geom in parent.findall("geom[@type='mesh']"))
            )
            self.assertIsNotNone(parent.find("geom[@name='bucket_visual']"))
            self.assertTrue(
                all(geom.get("density") == "0" for geom in parent.findall("geom") if geom.get("name") in names)
            )
            debug_parent = ET.parse(debug).getroot().find(
                ".//body[@name='stick_bucket_link']"
            )
            self.assertIsNotNone(
                debug_parent.find("geom[@name='bucket_proxy_frame_origin']")
            )
            for axis in "xyz":
                self.assertIsNotNone(
                    debug_parent.find(f"geom[@name='bucket_proxy_frame_axis_{axis}']")
                )
                self.assertIsNotNone(
                    debug_parent.find(f"geom[@name='stick_bucket_link_frame_axis_{axis}']")
                )
            self.assertIsNotNone(
                debug_parent.find("geom[@name='stick_bucket_link_frame_origin']")
            )

    def test_generation_is_deterministic_and_rejects_mujoco_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            first_dir, second_dir = directory / "first", directory / "second"
            first_dir.mkdir()
            second_dir.mkdir()
            first = self.generate(first_dir, config_text())
            second = self.generate(second_dir, config_text())
            self.assertEqual(first[0].returncode, 0, first[0].stderr)
            self.assertEqual(second[0].returncode, 0, second[0].stderr)
            self.assertEqual(first[1].read_bytes(), second[1].read_bytes())

            invalid_dir = directory / "invalid"
            invalid_dir.mkdir()
            invalid = config_text().replace(
                "    dimensions_m: [1.0, 2.0, 0.1]\n",
                "    dimensions_m: [1.0, 2.0, 0.1]\n    euler: [1, 0, 0]\n",
                1,
            )
            rejected = self.generate(invalid_dir, invalid)[0]
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("unknown keys", rejected.stderr)

    @unittest.skipUnless(FORGED_MODEL_AVAILABLE, "excavator Forge output is unavailable")
    def test_analyzer_reads_yaml_without_modifying_it(self):
        config = ROOT / "recipes/excavator/bucket-collision.yaml"
        before = config.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "sections.svg"
            result = subprocess.run(
                [
                    str(tools_python()),
                    str(ROOT / "tools/analyze_excavator_bucket_collision.py"),
                    "--mesh", str(FORGE_ROOT / "install/model/meshes/stick_bucket_link.STL"),
                    "--config", str(config),
                    "--output", str(output),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertEqual(config.read_bytes(), before)
            self.assertNotIn("proposal-json", result.args)

    @unittest.skipUnless(FORGED_MODEL_AVAILABLE, "excavator Forge output is unavailable")
    def test_accepted_proxy_passes_one_sphere_physical_validation(self):
        result = subprocess.run(
            [
                str(tools_python()),
                str(ROOT / "tools/validate_excavator_bucket_collision.py"),
                str(FORGE_ROOT / "install/excavator.soil.xml"),
                "--config",
                str(ROOT / "recipes/excavator/bucket-collision.yaml"),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["calibration_status"], "accepted")
        self.assertTrue(all(stage["passed"] for stage in payload["stages"].values()))


if __name__ == "__main__":
    unittest.main()
