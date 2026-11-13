#!/usr/bin/env python3
"""Generate and check a pick-and-place JointTrajectory for a two-jaw arm.

The tool reads the environment MJCF (robot, collision pads and the object),
solves inverse kinematics for a top-down grasp, and writes the joint targets
as a trajectory JSON for ``tools/control/send_joint_trajectory.py``:

    above the object -> descend with the jaws open -> close -> lift
    -> spin the wrist -> carry -> lower -> open -> retreat -> home

``--verify`` replays the written file in MuJoCo with the targets updated at
the Runtime controller rate, and reports from the simulated object pose whether
the object was lifted and placed. A failed check exits with status 1.

Frame convention (gripper site): x points from the wrist to the jaw tip and
the moving jaw closes along -z, the same as compute_gripper_pads.py.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import mujoco
import numpy as np


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model", type=Path, help="environment MJCF, e.g. so101.environment.xml")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--site", default="gripperframe")
    parser.add_argument("--object", default="grasp_cube", help="object body name")
    parser.add_argument("--arm-joints", nargs="+",
                        default=["shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex"],
                        help="joints solved by inverse kinematics; the first one turns the arm about the base")
    parser.add_argument("--wrist-roll-joint", default="wrist_roll")
    parser.add_argument("--gripper-joint", default="gripper")
    parser.add_argument("--open", type=float, default=1.2, help="gripper angle when open [rad]")
    parser.add_argument("--close", type=float, default=0.15,
                        help="gripper target when closed; below the contact angle so the jaws keep pressing [rad]")
    parser.add_argument("--grasp-depth", type=float, default=-0.004,
                        help="jaw tip height relative to the object centre at the grasp [m]")
    parser.add_argument("--approach", type=float, default=0.04, help="height above the object before descending [m]")
    parser.add_argument("--lift", type=float, default=0.05, help="lift height [m]")
    parser.add_argument("--spin", type=float, default=2.4, help="wrist roll swing while holding, 0 to skip [rad]")
    parser.add_argument("--place-angle-deg", type=float, default=46.0,
                        help="place position: object radius kept, rotated about the base by this angle")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--control-rate-hz", type=float, default=50.0)
    return parser.parse_args()


class Arm:
    def __init__(self, model, args):
        self.model = model
        self.site = model.site(args.site).id
        names = list(args.arm_joints) + [args.wrist_roll_joint, args.gripper_joint]
        self.names = names
        self.qadr = [model.joint(n).qposadr[0] for n in names]
        self.dadr = [model.joint(n).dofadr[0] for n in names]
        self.n_arm = len(args.arm_joints)

    def solve(self, target, seed):
        """Place the site at target with its x axis pointing down."""
        model, data = self.model, mujoco.MjData(self.model)
        q = seed.copy()
        for _ in range(400):
            data.qpos[self.qadr] = q
            mujoco.mj_forward(model, data)
            position_error = target - data.site_xpos[self.site]
            approach = data.site_xmat[self.site].reshape(3, 3)[:, 0]
            axis_error = np.cross(approach, [0.0, 0.0, -1.0])
            jac_pos = np.zeros((3, model.nv))
            jac_rot = np.zeros((3, model.nv))
            mujoco.mj_jacSite(model, data, jac_pos, jac_rot, self.site)
            cols = self.dadr[:self.n_arm]
            jac = np.vstack([jac_pos[:, cols], 0.3 * jac_rot[:, cols]])
            error = np.hstack([position_error, 0.3 * axis_error])
            q[:self.n_arm] += jac.T @ np.linalg.solve(jac @ jac.T + 1e-4 * np.eye(6), error)
            for i in range(self.n_arm):
                low, high = model.jnt_range[model.joint(self.names[i]).id]
                q[i] = min(max(q[i], low), high)
        tilt = math.degrees(math.acos(min(1.0, max(-1.0, -approach[2]))))
        return q, float(np.linalg.norm(position_error)), tilt

    def closing_axis(self, q):
        data = mujoco.MjData(self.model)
        data.qpos[self.qadr] = q
        mujoco.mj_forward(self.model, data)
        axis = data.site_xmat[self.site].reshape(3, 3)[:, 2].copy()
        axis[2] = 0.0
        return axis / np.linalg.norm(axis)


def object_state(model, data, body):
    joint = model.body_jntadr[body]
    adr = model.jnt_qposadr[joint]
    return data.qpos[adr:adr + 3].copy(), data.qpos[adr + 3:adr + 7].copy()


def build(model, args):
    arm = Arm(model, args)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    body = model.body(args.object).id
    center, _ = object_state(model, data, body)
    half_width = float(model.geom_size[model.body_geomadr[body]][0])

    home = np.zeros(len(arm.names))
    above, _, _ = arm.solve(center + [0, 0, args.approach], home)
    # Shift the tip so the object sits midway between the jaw pads.
    offset = arm.closing_axis(above) * half_width
    grasp_center = center - offset

    def solve(name, target, seed):
        q, error, tilt = arm.solve(target, seed)
        print(f"  {name:12s} position error {error * 1000:5.1f} mm, tilt {tilt:4.1f} deg")
        if error > 0.005 or tilt > 3.0:
            raise SystemExit(f"{name}: target not reachable with a top-down gripper")
        return q

    print("inverse kinematics:")
    above = solve("above", grasp_center + [0, 0, args.approach], above)
    grasp = solve("grasp", grasp_center + [0, 0, args.grasp_depth], above)
    lift = solve("lift", grasp_center + [0, 0, args.lift], above)
    angle = math.radians(args.place_angle_deg)
    rotate = np.array([[math.cos(angle), -math.sin(angle), 0], [math.sin(angle), math.cos(angle), 0], [0, 0, 1]])
    place_center = rotate @ grasp_center
    # The first arm joint turns the arm about the base; its sign depends on the
    # model, so start from both directions and keep the better solution.
    seeds = [lift + np.eye(len(lift))[0] * sign * angle for sign in (1.0, -1.0)]
    target = place_center + [0, 0, args.approach]
    best = min(seeds, key=lambda seed: arm.solve(target, seed)[1])
    place_above = solve("place above", target, best)
    place = solve("place", place_center + [0, 0, args.grasp_depth + 0.002], place_above)

    def pose(q, gripper, roll=0.0):
        values = q.copy()
        values[-2] = roll
        values[-1] = gripper
        return values

    keys = [
        (0.0, pose(home, 0.0)),
        (1.5, pose(above, args.open)),
        (3.0, pose(grasp, args.open)),
        (3.8, pose(grasp, args.open)),
        (4.6, pose(grasp, args.close)),
        (5.2, pose(grasp, args.close)),
        (6.8, pose(lift, args.close)),
    ]
    t = 6.8
    if args.spin:
        for roll, duration in ((args.spin, 1.2), (-args.spin, 1.4), (0.0, 1.2)):
            t += duration
            keys.append((t, pose(lift, args.close, roll)))
    for q, gripper, duration in (
        (place_above, args.close, 1.8), (place, args.close, 1.2), (place, args.close, 0.6),
        (place, args.open, 0.8), (place, args.open, 0.6), (place_above, args.open, 1.2),
        (home, 0.0, 1.5), (home, 0.0, 0.7),
    ):
        t += duration
        keys.append((t, pose(q, gripper)))

    trajectory = {
        "joint_names": arm.names,
        "points": [
            {"time_from_start": round(time, 3), "positions": [round(float(v), 4) for v in values]}
            for time, values in keys
        ],
    }
    lines = ["{", f'  "joint_names": {json.dumps(arm.names)},', '  "points": [']
    lines.append(",\n".join(f"    {json.dumps(point)}" for point in trajectory["points"]))
    lines += ["  ]", "}"]
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({len(keys)} points, {keys[-1][0]:.1f} s)")
    # The object sits offset from the tip, and the offset turns with the arm,
    # so the expected object position is the rotated object centre.
    return rotate @ center, half_width


def verify(model, args, place_center, half_width) -> bool:
    trajectory = json.loads(args.output.read_text(encoding="utf-8"))
    names = trajectory["joint_names"]
    times = np.array([p["time_from_start"] for p in trajectory["points"]])
    targets = np.array([p["positions"] for p in trajectory["points"]])
    actuators = []
    for name in names:
        joint_id = model.joint(name).id
        actuators.append(next(i for i in range(model.nu) if model.actuator_trnid[i, 0] == joint_id))
    data = mujoco.MjData(model)
    body = model.body(args.object).id
    start, _ = object_state(model, data, body)
    period = 1.0 / args.control_rate_hz
    next_update = 0.0
    max_height = start[2]
    while data.time < times[-1] + 2.0:
        if data.time >= next_update:
            data.ctrl[actuators] = [np.interp(data.time, times, targets[:, j]) for j in range(len(names))]
            next_update += period
        mujoco.mj_step(model, data)
        max_height = max(max_height, object_state(model, data, body)[0][2])
    end, quat = object_state(model, data, body)
    lifted = max_height - start[2]
    placed = float(np.linalg.norm(end[:2] - place_center[:2]))
    upright = 2 * math.degrees(math.acos(min(1.0, math.sqrt(quat[0] ** 2 + quat[3] ** 2))))
    print("verify (MuJoCo replay, targets updated at "
          f"{args.control_rate_hz:.0f} Hz):")
    print(f"  lifted by       {lifted * 1000:6.1f} mm   (needs >= {args.lift * 500:.0f} mm)")
    print(f"  placed off by   {placed * 1000:6.1f} mm   (needs <= {half_width * 1000:.0f} mm)")
    print(f"  tilted by       {upright:6.1f} deg  (needs <= 10 deg)")
    ok = lifted >= args.lift * 0.5 and placed <= half_width and upright <= 10.0
    print("  PASS" if ok else "  FAIL")
    return ok


def main() -> int:
    args = parse_args()
    model = mujoco.MjModel.from_xml_path(str(args.model))
    place_center, half_width = build(model, args)
    if args.verify and not verify(model, args, place_center, half_width):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
