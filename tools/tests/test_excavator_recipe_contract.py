from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORK_DIR = Path(os.environ.get("HAKONIWA_WORK_DIR", ROOT.parent / "hakoniwa-business-pack/work"))
MODEL_INSTALL = WORK_DIR / "model-forge/excavator/install"
FORGED_MODEL_AVAILABLE = (MODEL_INSTALL / "excavator.mobile.xml").is_file()
JOINTS = [
    "base_chassis_joint",
    "chassis_boom_joint",
    "boom_stick_joint",
    "stick_bucket_joint",
]


class ExcavatorRecipeContractTest(unittest.TestCase):
    def test_manifest_and_bindings_cover_four_excavator_joints(self):
        recipe = ROOT / "recipes" / "excavator"
        manifest = json.loads((recipe / "asset-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["model"], "excavator.mobile.xml")
        digging_manifest = json.loads(
            (recipe / "asset-manifest-digging.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            digging_manifest["model"], "excavator.soil.xml"
        )
        actuator = json.loads(
            (recipe / "config/actuator/joint/excavator_joints.json").read_text(encoding="utf-8")
        )
        states = json.loads(
            (recipe / "config/sensors/joint_state/excavator-joint-states.json").read_text(encoding="utf-8")
        )
        self.assertEqual([item["name"] for item in actuator["spec"]["joints"]], JOINTS)
        self.assertEqual([item["name"] for item in states["spec"]["joints"]], JOINTS)

    @unittest.skipUnless(FORGED_MODEL_AVAILABLE, "excavator Forge output is unavailable")
    def test_runtime_mjcf_contains_matching_joints_and_actuators(self):
        model_path = MODEL_INSTALL / "excavator.runtime.xml"
        model = ET.parse(model_path).getroot()
        self.assertEqual(
            [joint.get("name") for joint in model.findall(".//joint") if joint.get("name")],
            JOINTS,
        )
        self.assertEqual(
            [item.get("joint") for item in model.findall("./actuator/position")],
            JOINTS,
        )
        self.assertEqual(len(model.findall("./contact/exclude")), 4)

    @unittest.skipUnless(FORGED_MODEL_AVAILABLE, "excavator Forge output is unavailable")
    def test_mobile_mjcf_adds_free_base_floor_and_six_velocity_wheels(self):
        model = ET.parse(
            MODEL_INSTALL / "excavator.mobile.xml"
        ).getroot()
        self.assertIsNotNone(model.find(".//freejoint[@name='base_freejoint']"))
        floor = model.find("./worldbody/geom[@name='excavator_floor']")
        self.assertIsNotNone(floor)
        self.assertEqual(floor.get("rgba"), "0.38 0.25 0.12 1")
        self.assertIsNotNone(model.find("./asset/texture[@name='excavator_sky']"))
        self.assertIsNotNone(model.find("./worldbody/light[@name='excavator_daylight']"))
        wheel_joints = [
            joint.get("name")
            for joint in model.findall(".//joint")
            if "track_wheel" in (joint.get("name") or "")
        ]
        self.assertEqual(len(wheel_joints), 6)
        wheel_motors = model.findall("./actuator/velocity")
        self.assertEqual(len(wheel_motors), 6)
        for motor in wheel_motors:
            self.assertEqual(float(motor.get("kv")), 20000.0)
            self.assertEqual(
                [float(value) for value in motor.get("forcerange").split()],
                [-100000.0, 100000.0],
            )
        for geom in model.findall("./worldbody/body[@name='base_link']/geom[@type='mesh']"):
            self.assertEqual(geom.get("contype"), "0")
            self.assertEqual(geom.get("conaffinity"), "0")
        bucket_collision = model.find(
            ".//body[@name='stick_bucket_link']/geom[@type='mesh'][@contype='1']"
        )
        self.assertIsNotNone(bucket_collision)
        yellow_visual = model.find(
            ".//body[@name='stick_bucket_link']/geom[@type='mesh'][@group='1']"
        )
        self.assertEqual(yellow_visual.get("rgba"), "0.95 0.62 0.05 1")
        home = model.find("./keyframe/key[@name='excavator_home']")
        self.assertIsNotNone(home)
        home_qpos = [float(value) for value in home.get("qpos").split()]
        self.assertEqual(home_qpos[7:11], [0.0, 0.6, 0.0, -1.5])

    def test_mobile_base_manifest_and_twist_channel_are_consistent(self):
        recipe = ROOT / "recipes" / "excavator"
        manifest = json.loads((recipe / "asset-manifest.json").read_text(encoding="utf-8"))
        components = {item["id"]: item for item in manifest["components"]}
        mobile = components["mobile_base"]
        drive = json.loads((recipe / mobile["config"]).read_text(encoding="utf-8"))
        pdu_types = json.loads(
            (recipe / "config/pdu/excavator-pdutypes.json").read_text(encoding="utf-8")
        )
        self.assertEqual(mobile["pdu_robot"], "Excavator")
        self.assertEqual(drive["pdu_config"]["pdu_name"], "cmd_vel")
        self.assertEqual(len(drive["spec"]["left_actuator_components"]), 3)
        self.assertEqual(len(drive["spec"]["right_actuator_components"]), 3)
        cmd_vel = next(item for item in pdu_types if item["name"] == "cmd_vel")
        self.assertEqual(cmd_vel["type"], "geometry_msgs/Twist")
        self.assertEqual(cmd_vel["pdu_size"], 72)

    @unittest.skipUnless(FORGED_MODEL_AVAILABLE, "excavator Forge output is unavailable")
    def test_soil_model_is_recipe_generated_and_keeps_mobile_model_clean(self):
        recipe = ROOT / "recipes" / "excavator"
        config = json.loads(
            (recipe / "config/environment/soil.json").read_text(encoding="utf-8")
        )
        self.assertTrue(config["enabled"])
        particle_count = (
            config["grid_count"][0]
            * config["grid_count"][1]
            * config["grid_count"][2]
        )
        self.assertGreater(particle_count, 0)

        mobile = ET.parse(MODEL_INSTALL / "excavator.mobile.xml").getroot()
        self.assertIsNone(mobile.find(".//body[@name='excavator_soil_sphere_001']"))

        soil = ET.parse(MODEL_INSTALL / "excavator.soil.xml").getroot()
        particles = soil.findall("./worldbody/body")
        particles = [
            body
            for body in particles
            if (body.get("name") or "").startswith("excavator_soil_sphere_")
        ]
        self.assertEqual(len(particles), particle_count)
        particle = particles[0]
        self.assertIsNotNone(particle.find("freejoint"))
        self.assertEqual(len(particle.findall("joint")), 0)
        geom = particle.find("geom[@type='sphere']")
        self.assertEqual(geom.get("size"), str(config["particle_radius_m"]))
        self.assertEqual(geom.get("condim"), str(config["contact_condim"]))
        self.assertEqual(
            [float(value) for value in geom.get("friction").split()],
            config["friction"],
        )
        self.assertEqual(geom.get("contype"), "1")
        self.assertEqual(geom.get("conaffinity"), "1")
        self.assertEqual(soil.find("./size").get("memory"), "512M")

        home = soil.find("./keyframe/key[@name='excavator_home']")
        # Excavator nq=17 plus seven freejoint coordinates per sphere.
        self.assertEqual(len(home.get("qpos").split()), 17 + 7 * particle_count)

    @unittest.skipUnless(FORGED_MODEL_AVAILABLE, "excavator Forge output is unavailable")
    def test_hfield_work_pit_replaces_plane_without_lowering_launch_ground(self):
        recipe = ROOT / "recipes" / "excavator"
        config = json.loads(
            (recipe / "config/environment/terrain.json").read_text(encoding="utf-8")
        )
        model = ET.parse(MODEL_INSTALL / "excavator.terrain.xml").getroot()
        hfield = model.find("./asset/hfield[@name='excavator_worksite_hfield']")
        self.assertIsNotNone(hfield)
        self.assertEqual(hfield.get("file"), "excavator-worksite-height.png")
        self.assertTrue(
            (MODEL_INSTALL / "excavator-worksite-height.png").is_file()
        )
        floor = model.find("./worldbody/geom[@name='excavator_floor']")
        self.assertEqual(floor.get("type"), "hfield")
        self.assertEqual(floor.get("hfield"), "excavator_worksite_hfield")
        self.assertEqual(
            float(floor.get("pos").split()[2]), -config["max_depth_m"]
        )
        self.assertEqual(config["pit_center_m"], [9.0, 0.0])
        self.assertEqual(config["pit_floor_radius_m"], [2.0, 1.4])
        self.assertEqual(config["pit_rim_radius_m"], [2.733333334, 2.0])
        # The pit rim ends before the crawler home position at world origin.
        self.assertGreater(
            abs(config["pit_center_m"][0]), config["pit_rim_radius_m"][0]
        )

    @unittest.skipUnless(FORGED_MODEL_AVAILABLE, "excavator Forge output is unavailable")
    def test_bucket_collision_is_generated_from_the_five_part_calibration(self):
        model = ET.parse(MODEL_INSTALL / "excavator.bucket.xml").getroot()
        bucket = model.find(".//body[@name='stick_bucket_link']")
        mesh_geoms = bucket.findall("geom[@type='mesh']")
        self.assertEqual(len(mesh_geoms), 2)
        self.assertTrue(all(geom.get("contype") == "0" for geom in mesh_geoms))
        collision_geoms = [
            geom
            for geom in bucket.findall("geom")
            if (geom.get("name") or "").startswith("bucket_proxy_")
        ]
        collision_names = {geom.get("name") for geom in collision_geoms}
        self.assertEqual(
            collision_names,
            {
                "bucket_proxy_floor",
                "bucket_proxy_back",
                "bucket_proxy_side_left",
                "bucket_proxy_side_right",
                "bucket_proxy_cutting_edge",
            },
        )
        self.assertNotIn("bucket_proxy_front", collision_names)
        self.assertNotIn("bucket_proxy_ceiling", collision_names)
        self.assertTrue(all(geom.get("type") == "box" for geom in collision_geoms))
        self.assertTrue(all(geom.get("density") == "0" for geom in collision_geoms))
        self.assertTrue(
            all(float(geom.get("rgba").split()[3]) == 0.0 for geom in collision_geoms)
        )

        debug_model = ET.parse(
            MODEL_INSTALL / "excavator.bucket-proxy-debug.xml"
        ).getroot()
        debug_bucket = debug_model.find(".//body[@name='stick_bucket_link']")
        debug_collision_geoms = [
            geom
            for geom in debug_bucket.findall("geom")
            if (geom.get("name") or "").startswith("bucket_proxy_")
            and "frame" not in (geom.get("name") or "")
        ]
        self.assertEqual(len(debug_collision_geoms), 5)
        self.assertTrue(
            all(float(geom.get("rgba").split()[3]) > 0.0 for geom in debug_collision_geoms)
        )

    @unittest.skipUnless(FORGED_MODEL_AVAILABLE, "excavator Forge output is unavailable")
    def test_particle_model_uses_recipe_tuned_arm_gains(self):
        model = ET.parse(MODEL_INSTALL / "excavator.soil.xml").getroot()
        gains = {
            actuator.get("name"): float(actuator.get("kp"))
            for actuator in model.findall("./actuator/position")
        }
        self.assertEqual(
            gains,
            {
                "base_chassis_joint_motor": 10_000_000.0,
                "chassis_boom_joint_motor": 10_000_000.0,
                "boom_stick_joint_motor": 5_000_000.0,
                "stick_bucket_joint_motor": 2_000_000.0,
            },
        )

    @unittest.skipUnless(FORGED_MODEL_AVAILABLE, "excavator Forge output is unavailable")
    def test_soil_generator_is_deterministic(self):
        generator = ROOT / "tools/generate_excavator_soil.py"
        source = MODEL_INSTALL / "excavator.mobile.xml"
        config = ROOT / "recipes/excavator/config/environment/soil.json"
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.xml"
            second = Path(directory) / "second.xml"
            for output in (first, second):
                result = subprocess.run(
                    [
                        "python3",
                        str(generator),
                        str(source),
                        "--config",
                        str(config),
                        "--output",
                        str(output),
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    @unittest.skipUnless(FORGED_MODEL_AVAILABLE, "excavator Forge output is unavailable")
    def test_hfield_generator_is_deterministic(self):
        generator = ROOT / "tools/generate_excavator_hfield.py"
        source = MODEL_INSTALL / "excavator.mobile.xml"
        config = ROOT / "recipes/excavator/config/environment/terrain.json"
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            images = []
            for index in range(2):
                run_directory = Path(directory) / str(index)
                run_directory.mkdir()
                output = run_directory / "terrain.xml"
                image = run_directory / "height.png"
                result = subprocess.run(
                    [
                        "python3",
                        str(generator),
                        str(source),
                        "--config",
                        str(config),
                        "--heightmap-output",
                        str(image),
                        "--output",
                        str(output),
                    ],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                outputs.append(output.read_bytes())
                images.append(image.read_bytes())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(images[0], images[1])

    def test_common_controller_exposes_separate_auto_and_manual_inputs(self):
        recipe = ROOT / "recipes" / "excavator"
        manifest = json.loads((recipe / "asset-manifest.json").read_text(encoding="utf-8"))
        components = {item["id"]: item for item in manifest["components"]}
        controller_component = components["excavator_controller"]
        controller = json.loads(
            (recipe / controller_component["config"]).read_text(encoding="utf-8")
        )["spec"]
        self.assertEqual(controller_component["pdu_robot"], "Excavator")
        self.assertEqual(controller["manual_timeout_sec"], 0.5)
        self.assertEqual(len(controller["manual_joint_actuator_components"]), 4)
        self.assertEqual(len(controller["manual_joint_velocity_limits_rad_s"]), 4)
        for component_id in controller["manual_joint_actuator_components"]:
            self.assertIn(component_id, components)

        pdu_types = json.loads(
            (recipe / "config/pdu/excavator-pdutypes.json").read_text(encoding="utf-8")
        )
        channels = {item["name"]: item for item in pdu_types}
        self.assertEqual(
            channels[controller["manual_joint_velocity_pdu"]]["type"],
            "std_msgs/Float64MultiArray",
        )
        self.assertEqual(
            channels[controller["manual_cmd_vel_pdu"]]["type"],
            "geometry_msgs/Twist",
        )

        source = (ROOT / "src/controllers/excavator_controller.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("trajectory_->ClearTrajectory()", source)
        self.assertIn("Ignored JointTrajectory while MANUAL is active", source)
        self.assertIn("manual timeout: holding arm and stopping base", source)

    def test_manual_demo_matches_controller_joint_count(self):
        demo = json.loads(
            (ROOT / "recipes/excavator/demo-manual.json").read_text(encoding="utf-8")
        )
        self.assertGreaterEqual(demo["send_rate_hz"], 10.0)
        self.assertTrue(demo["commands"])
        for command in demo["commands"]:
            self.assertEqual(len(command["joint_velocity_rad_s"]), len(JOINTS))

    @unittest.skipUnless(FORGED_MODEL_AVAILABLE, "excavator Forge output is unavailable")
    def test_materialized_model_checksums_match(self):
        robot_root = MODEL_INSTALL
        for line in (robot_root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
            expected, relative_path = line.split(maxsplit=1)
            payload = (robot_root / relative_path).read_bytes()
            self.assertEqual(hashlib.sha256(payload).hexdigest(), expected)

    def test_operator_help_is_available(self):
        result = subprocess.run(
            ["python3", str(ROOT / "tools/recipe/excavator.py"), "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MathScavator9000 Excavator", result.stdout)
        self.assertIn("bucket-proxy", result.stdout)
        self.assertIn("--digging-worksite", result.stdout)
        self.assertIn("--realtime-sync-cycle-msec", result.stdout)

    def test_excavator_runtime_is_separate_from_generic_arm_runtime(self):
        generic = (ROOT / "apps/robot-arm/robot-arm-hakoniwa-asset.cpp").read_text(
            encoding="utf-8"
        )
        excavator = (
            ROOT / "apps/excavator/robot-excavator-hakoniwa-asset.cpp"
        ).read_text(encoding="utf-8")
        mobile = (ROOT / "src/controllers/excavator_mobile_base.cpp").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("ExcavatorMobileBase", generic)
        self.assertNotIn("cmd_vel", generic)
        self.assertIn("ExcavatorMobileBase", excavator)
        self.assertIn("ToWheelVelocityTargets", mobile)
        self.assertIn('argument == "--realtime-sync-cycle-msec"', excavator)
        self.assertIn("realtime_pacer.pace(simulation_time_sec)", excavator)
        self.assertNotIn('argument == "--real-sleep"', excavator)

    def test_demo_operator_runs_drive_before_arm(self):
        demo = (ROOT / "recipes/excavator/demos/send_excavator_demo.py").read_text(
            encoding="utf-8"
        )
        self.assertLess(demo.index("crawler travel"), demo.index("arm operation"))
        self.assertIn("send_twist_sequence.py", demo)
        self.assertIn("send_joint_trajectory.py", demo)
        self.assertNotIn('"--keep-alive"', demo)
        self.assertIn("connection-free operator", demo)
        recipe_tool = (ROOT / "tools/recipe/common/arm.py").read_text(encoding="utf-8")
        self.assertIn("--manual-demo", recipe_tool)
        self.assertIn("--ps5-controller", recipe_tool)
        mapping = json.loads(
            (ROOT / "recipes/excavator/ps5-controller-macos.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("deadman", mapping["buttons"])
        ps5_controller = (
            ROOT / "tools/control/ps5_excavator_manual.py"
        ).read_text(encoding="utf-8")
        self.assertIn("pygame.event.get()", ps5_controller)
        self.assertNotIn("pygame.event.pump()", ps5_controller)

        trajectory = json.loads(
            (ROOT / "recipes/excavator/demo-trajectory.json").read_text(
                encoding="utf-8"
            )
        )
        safe_home = [0.0, 0.6, 0.0, -1.5]
        self.assertEqual(trajectory["points"][0]["positions"], safe_home)
        self.assertEqual(trajectory["points"][-1]["positions"], safe_home)


if __name__ == "__main__":
    unittest.main()
