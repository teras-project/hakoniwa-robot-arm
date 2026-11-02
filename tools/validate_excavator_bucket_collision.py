#!/usr/bin/env python3
"""One-sphere physical validation after human bucket-proxy calibration."""

from __future__ import annotations

import argparse
import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np

from generate_excavator_bucket_collision import load_bucket_collision, rpy_deg_matrix


SPHERE_BODY = "excavator_soil_sphere_001"
SPHERE_GEOM = "excavator_soil_sphere_001_geom"
BUCKET_BODY = "stick_bucket_link"
BUCKET_JOINT = "stick_bucket_joint"
BUCKET_ACTUATOR = "stick_bucket_joint_motor"


def load_one_sphere_model(model_path: Path) -> mujoco.MjModel:
    """Load the generated worksite while retaining only soil sphere 001.

    The runtime model may contain thousands of free bodies. Integrating all of
    them in a one-sphere collision regression would make the regression test
    measure granular-soil performance instead of bucket continuity.
    """
    tree = ET.parse(model_path)
    root = tree.getroot()
    worldbody = root.find("worldbody")
    if worldbody is None:
        raise RuntimeError("validation model is missing worldbody")
    soil_bodies = [
        body
        for body in worldbody.findall("body")
        if (body.get("name") or "").startswith("excavator_soil_sphere_")
    ]
    if not any(body.get("name") == SPHERE_BODY for body in soil_bodies):
        raise RuntimeError(f"validation model is missing {SPHERE_BODY}")
    removed_count = 0
    for body in soil_bodies:
        if body.get("name") != SPHERE_BODY:
            worldbody.remove(body)
            removed_count += 1
    if removed_count:
        for key in root.findall("./keyframe/key"):
            qpos = key.get("qpos")
            if qpos is not None:
                values = qpos.split()
                trim = 7 * removed_count
                if len(values) <= trim:
                    raise RuntimeError("validation keyframe qpos is shorter than soil suffix")
                key.set("qpos", " ".join(values[:-trim]))
            qvel = key.get("qvel")
            if qvel is not None:
                values = qvel.split()
                trim = 6 * removed_count
                if len(values) <= trim:
                    raise RuntimeError("validation keyframe qvel is shorter than soil suffix")
                key.set("qvel", " ".join(values[:-trim]))
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=".xml", dir=model_path.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
        tree.write(temporary, encoding="utf-8", xml_declaration=True)
    try:
        return mujoco.MjModel.from_xml_path(str(temporary_path))
    finally:
        temporary_path.unlink(missing_ok=True)


def object_id(model, object_type, name):
    result = mujoco.mj_name2id(model, object_type, name)
    if result < 0:
        raise RuntimeError(f"missing MuJoCo object: {name}")
    return result


class Harness:
    def __init__(self, model_path: Path, config: dict):
        self.config = config
        self.model = load_one_sphere_model(model_path)
        self.data = mujoco.MjData(self.model)
        self.bucket_body = object_id(self.model, mujoco.mjtObj.mjOBJ_BODY, BUCKET_BODY)
        self.sphere_body = object_id(self.model, mujoco.mjtObj.mjOBJ_BODY, SPHERE_BODY)
        self.sphere_geom = object_id(self.model, mujoco.mjtObj.mjOBJ_GEOM, SPHERE_GEOM)
        self.bucket_joint = object_id(self.model, mujoco.mjtObj.mjOBJ_JOINT, BUCKET_JOINT)
        self.bucket_actuator = object_id(
            self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, BUCKET_ACTUATOR
        )
        self.floor_geom = object_id(
            self.model, mujoco.mjtObj.mjOBJ_GEOM, "bucket_proxy_floor"
        )
        sphere_joint = self.model.body_jntadr[self.sphere_body]
        self.sphere_qpos_address = self.model.jnt_qposadr[sphere_joint]
        self.sphere_dof_address = self.model.jnt_dofadr[sphere_joint]
        self.bucket_qpos_address = self.model.jnt_qposadr[self.bucket_joint]
        self.radius_m = float(self.model.geom_size[self.sphere_geom][0])
        self.frame_origin = np.asarray(config["frame"]["origin_in_parent_m"], dtype=float)
        self.frame_rotation = np.asarray(
            rpy_deg_matrix(config["frame"]["rpy_deg"]), dtype=float
        )
        self.contacts: set[str] = set()

        for body_id in range(self.model.nbody):
            body_name = (
                mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_BODY, body_id) or ""
            )
            if not body_name.startswith("excavator_soil_sphere_") or body_name == SPHERE_BODY:
                continue
            first_geom = self.model.body_geomadr[body_id]
            geom_count = self.model.body_geomnum[body_id]
            for geom_id in range(first_geom, first_geom + geom_count):
                self.model.geom_contype[geom_id] = 0
                self.model.geom_conaffinity[geom_id] = 0

        self.home_key = object_id(
            self.model, mujoco.mjtObj.mjOBJ_KEY, "excavator_home"
        )
        mujoco.mj_resetDataKeyframe(self.model, self.data, self.home_key)
        self.catch_qpos = self.find_catch_qpos()
        self.data.qpos[self.bucket_qpos_address] = self.catch_qpos
        self.data.ctrl[self.bucket_actuator] = self.catch_qpos
        mujoco.mj_forward(self.model, self.data)
        self.base_qpos = self.data.qpos[:7].copy()

    def find_catch_qpos(self) -> float:
        lower, upper = self.model.jnt_range[self.bucket_joint]
        best_qpos = float(upper)
        best_alignment = -float("inf")
        for qpos in np.linspace(lower, upper, 101):
            self.data.qpos[self.bucket_qpos_address] = qpos
            mujoco.mj_forward(self.model, self.data)
            floor_normal = self.data.geom_xmat[self.floor_geom].reshape(3, 3)[:, 2]
            alignment = float(floor_normal @ np.asarray([0.0, 0.0, 1.0]))
            if alignment > best_alignment:
                best_alignment = alignment
                best_qpos = float(qpos)
        return best_qpos

    def bucket_world_transform(self):
        rotation = self.data.xmat[self.bucket_body].reshape(3, 3).copy()
        return rotation, self.data.xpos[self.bucket_body].copy()

    def proxy_to_parent(self, point):
        return self.frame_origin + self.frame_rotation @ np.asarray(point, dtype=float)

    def parent_to_proxy(self, point):
        return self.frame_rotation.T @ (np.asarray(point, dtype=float) - self.frame_origin)

    def place_sphere_over_floor(self, lateral_velocity_m_s=0.0):
        floor = self.config["parts"]["floor"]
        floor_rotation = np.asarray(rpy_deg_matrix(floor["rpy_deg"]), dtype=float)
        floor_center = np.asarray(floor["center_m"], dtype=float)
        clearance = floor["dimensions_m"][2] / 2.0 + self.radius_m + 0.30
        proxy_position = floor_center + floor_rotation[:, 2] * clearance
        parent_position = self.proxy_to_parent(proxy_position)
        bucket_rotation, bucket_position = self.bucket_world_transform()
        address = self.sphere_qpos_address
        self.data.qpos[address : address + 3] = bucket_position + bucket_rotation @ parent_position
        self.data.qpos[address + 3 : address + 7] = [1.0, 0.0, 0.0, 0.0]
        self.data.qvel[:] = 0.0
        proxy_velocity = np.asarray([lateral_velocity_m_s, 0.0, 0.0])
        self.data.qvel[self.sphere_dof_address : self.sphere_dof_address + 3] = (
            bucket_rotation @ (self.frame_rotation @ proxy_velocity)
        )
        mujoco.mj_forward(self.model, self.data)

    def sphere_proxy_position(self):
        bucket_rotation, bucket_position = self.bucket_world_transform()
        parent_position = bucket_rotation.T @ (
            self.data.xpos[self.sphere_body] - bucket_position
        )
        return self.parent_to_proxy(parent_position)

    def record_contacts(self):
        for contact_index in range(self.data.ncon):
            contact = self.data.contact[contact_index]
            names = {
                mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_GEOM, contact.geom1),
                mujoco.mj_id2name(self.model, mujoco.mjtObj.mjOBJ_GEOM, contact.geom2),
            }
            if SPHERE_GEOM in names:
                self.contacts.update(name for name in names if name)

    def step(self, count: int, start_qpos: float, target_qpos: float, observer=None):
        for index in range(count):
            ratio = (index + 1) / count
            target = start_qpos + (target_qpos - start_qpos) * ratio
            self.data.qpos[:7] = self.base_qpos
            self.data.qvel[:6] = 0.0
            self.data.ctrl[self.bucket_actuator] = target
            mujoco.mj_step(self.model, self.data)
            self.record_contacts()
            if observer is not None:
                observer(self)

    def interior_limits(self):
        parts = self.config["parts"]
        left, right = parts["side_left"], parts["side_right"]
        left_inner = left["center_m"][0] + left["dimensions_m"][0] / 2.0
        right_inner = right["center_m"][0] - right["dimensions_m"][0] / 2.0
        x_min = min(left_inner, right_inner) + self.radius_m
        x_max = max(left_inner, right_inner) - self.radius_m
        y_values = [
            parts["cutting_edge"]["center_m"][1],
            parts["back"]["center_m"][1],
        ]
        return x_min, x_max, min(y_values), max(y_values)

    def is_inside_plan_view(self, point, tolerance=0.08):
        x_min, x_max, y_min, y_max = self.interior_limits()
        return bool(
            x_min - tolerance <= point[0] <= x_max + tolerance
            and y_min - tolerance <= point[1] <= y_max + tolerance
        )


def run_validation(model_path: Path, config: dict) -> dict:
    harness = Harness(model_path, config)
    harness.place_sphere_over_floor()
    harness.step(1200, harness.catch_qpos, harness.catch_qpos)
    static_position = harness.sphere_proxy_position()
    static_contacts = sorted(harness.contacts)
    static_passed = bool(
        harness.is_inside_plan_view(static_position)
        and "bucket_proxy_floor" in harness.contacts
    )

    hold_qpos = max(
        float(harness.model.jnt_range[harness.bucket_joint][0]),
        harness.catch_qpos - 0.8,
    )
    harness.contacts.clear()
    harness.step(1500, harness.catch_qpos, hold_qpos)
    harness.step(500, hold_qpos, hold_qpos)
    hold_position = harness.sphere_proxy_position()
    hold_contacts = sorted(harness.contacts)
    hold_passed = bool(
        harness.is_inside_plan_view(hold_position)
        and any(name.startswith("bucket_proxy_") for name in harness.contacts)
    )

    dump_qpos = float(harness.model.jnt_range[harness.bucket_joint][0]) + 0.05
    harness.step(1800, hold_qpos, dump_qpos)
    harness.step(700, dump_qpos, dump_qpos)
    dump_position = harness.sphere_proxy_position()
    bucket_extent = max(
        max(part["dimensions_m"])
        for part in config["parts"].values()
        if part["enabled"]
    )
    dump_distance = float(np.linalg.norm(dump_position))
    dump_passed = bool(
        dump_distance > bucket_extent + harness.radius_m
        and not harness.is_inside_plan_view(dump_position)
    )

    side_harness = Harness(model_path, config)
    side_harness.place_sphere_over_floor(lateral_velocity_m_s=2.0)
    maximum_x = -float("inf")

    def observe_side(current):
        nonlocal maximum_x
        maximum_x = max(maximum_x, float(current.sphere_proxy_position()[0]))

    side_harness.step(
        1500, side_harness.catch_qpos, side_harness.catch_qpos, observe_side
    )
    _, x_max, _, _ = side_harness.interior_limits()
    side_passed = bool(
        maximum_x <= x_max + 0.08
        and "bucket_proxy_side_right" in side_harness.contacts
    )

    stages = {
        "static_entry_and_settle": {
            "passed": static_passed,
            "sphere_proxy_position_m": static_position.tolist(),
            "contacts": static_contacts,
        },
        "side_containment": {
            "passed": side_passed,
            "maximum_sphere_center_x_m": maximum_x,
            "allowed_maximum_x_m": x_max + 0.08,
            "contacts": sorted(side_harness.contacts),
        },
        "slow_curl_hold": {
            "passed": hold_passed,
            "sphere_proxy_position_m": hold_position.tolist(),
            "contacts": hold_contacts,
        },
        "dump": {
            "passed": dump_passed,
            "sphere_proxy_position_m": dump_position.tolist(),
            "distance_from_proxy_origin_m": dump_distance,
        },
    }
    return {
        "status": "passed" if all(item["passed"] for item in stages.values()) else "failed",
        "calibration_status": config["calibration"]["status"],
        "catch_bucket_qpos_rad": harness.catch_qpos,
        "hold_bucket_qpos_rad": hold_qpos,
        "dump_bucket_qpos_rad": dump_qpos,
        "sphere_radius_m": harness.radius_m,
        "stages": stages,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    config = load_bucket_collision(args.config)
    if config["calibration"]["status"] != "accepted":
        result = {
            "status": "blocked_manual_calibration",
            "calibration_status": config["calibration"]["status"],
            "automatic_guarantees": [],
            "reason": "A person must first approve the five-part proxy in the Viewer.",
        }
        return_code = 3
    else:
        result = run_validation(args.model, config)
        return_code = 0 if result["status"] == "passed" else 1
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(payload, end="")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
