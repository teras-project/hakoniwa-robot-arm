#!/usr/bin/env python3
"""Compute flat collision pads for a two-jaw gripper from its jaw meshes.

Curved jaw meshes collide through their convex hulls, so a held object only
touches the jaw tips and slips out. This tool measures the inner faces of the
fixed and moving jaw collision meshes and places one thin box on each, parallel
to each other at the gripper angle where the gap equals the object width. The
output is the ``robot_collision_pads`` array for
``recipes/<robot>/config/environment/workspace.json``; the environment
generator then replaces the jaw hulls with these pads.

Frame convention (gripper site): x points from the wrist to the jaw tip, and
the moving jaw closes towards the fixed jaw along -z. The fixed jaw lies on the
-z side of z = 0 near the tip.
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
    parser.add_argument("model", type=Path, help="forged robot MJCF, e.g. so101.xml")
    parser.add_argument("--site", default="gripperframe")
    parser.add_argument("--gripper-joint", default="gripper")
    parser.add_argument("--fixed-body", default="gripper")
    parser.add_argument("--fixed-mesh", default="wrist_roll_follower_so101_v1")
    parser.add_argument("--moving-body", default="moving_jaw_so101_v1")
    parser.add_argument("--moving-mesh", default="moving_jaw_so101_v1")
    parser.add_argument("--object-width", type=float, default=0.03,
                        help="width of the object between the jaws [m]")
    parser.add_argument("--pad-length", type=float, default=0.04,
                        help="pad length measured back from the jaw tip [m]")
    parser.add_argument("--half-size", type=float, nargs=3,
                        default=[0.02, 0.006, 0.0015],
                        help="box half sizes along site x, y, z [m]")
    parser.add_argument("--friction", type=float, nargs=3, default=[2.0, 0.02, 0.001])
    parser.add_argument("--max-angle", type=float, default=1.2,
                        help="upper end of the gripper angle search; the jaw tip must stay within --pad-length [rad]")
    parser.add_argument("--output", type=Path, help="write the JSON array here")
    return parser.parse_args()


def mesh_points_in_site(model, data, body_name, mesh_name, site_id):
    """Collision mesh vertices of one body, expressed in the site frame."""
    body_id = model.body(body_name).id
    mesh_id = model.mesh(mesh_name).id
    geoms = [
        g for g in range(model.ngeom)
        if model.geom_bodyid[g] == body_id
        and model.geom_dataid[g] == mesh_id
        and model.geom_contype[g] != 0
    ]
    if not geoms:
        raise SystemExit(f"no colliding geom with mesh {mesh_name} on body {body_name}")
    geom_id = geoms[0]
    start = model.mesh_vertadr[mesh_id]
    vertices = model.mesh_vert[start:start + model.mesh_vertnum[mesh_id]]
    world = (data.geom_xmat[geom_id].reshape(3, 3) @ vertices.T).T + data.geom_xpos[geom_id]
    site_rot = data.site_xmat[site_id].reshape(3, 3)
    return (site_rot.T @ (world - data.site_xpos[site_id]).T).T


def inner_faces(model, data, args, site_id):
    """Inner face z of the fixed and moving jaws near the tip (site frame)."""
    fixed = mesh_points_in_site(model, data, args.fixed_body, args.fixed_mesh, site_id)
    moving = mesh_points_in_site(model, data, args.moving_body, args.moving_mesh, site_id)
    near = lambda p: p[(p[:, 0] > -args.pad_length) & (p[:, 0] < 0.0)]
    return near(fixed)[:, 2].max(), near(moving)[:, 2].min()


def rpy_degrees(rotation):
    """Roll, pitch, yaw (Z-Y-X) in degrees, stable at pitch = +-90 deg."""
    if abs(rotation[2, 0]) > 0.9999:
        pitch = -math.copysign(math.pi / 2, rotation[2, 0])
        return [0.0, math.degrees(pitch), math.degrees(math.atan2(-rotation[0, 1], rotation[1, 1]))]
    roll = math.atan2(rotation[2, 1], rotation[2, 2])
    pitch = math.asin(-rotation[2, 0])
    yaw = math.atan2(rotation[1, 0], rotation[0, 0])
    return [math.degrees(roll), math.degrees(pitch), math.degrees(yaw)]


def main() -> int:
    args = parse_args()
    model = mujoco.MjModel.from_xml_path(str(args.model))
    data = mujoco.MjData(model)
    site_id = model.site(args.site).id
    joint = model.joint(args.gripper_joint)
    qadr = joint.qposadr[0]
    low = model.jnt_range[joint.id][0]
    high = min(model.jnt_range[joint.id][1], args.max_angle)

    def gap_at(q):
        data.qpos[:] = 0.0
        data.qpos[qadr] = q
        mujoco.mj_forward(model, data)
        fixed_z, moving_z = inner_faces(model, data, args, site_id)
        return moving_z - fixed_z

    if not gap_at(low) < args.object_width < gap_at(high):
        raise SystemExit("object width is outside the gripper opening range")
    for _ in range(60):
        mid = 0.5 * (low + high)
        if gap_at(mid) < args.object_width:
            low = mid
        else:
            high = mid
    grip_angle = 0.5 * (low + high)
    gap_at(grip_angle)
    fixed_z, moving_z = inner_faces(model, data, args, site_id)

    site_pos = data.site_xpos[site_id]
    site_rot = data.site_xmat[site_id].reshape(3, 3)
    half = args.half_size
    pads = []
    for name, body, mesh, z in (
        ("fixed_jaw_pad", args.fixed_body, args.fixed_mesh, fixed_z - half[2]),
        ("moving_jaw_pad", args.moving_body, args.moving_mesh, moving_z + half[2]),
    ):
        body_id = model.body(body).id
        body_rot = data.xmat[body_id].reshape(3, 3)
        center_world = site_pos + site_rot @ np.array([-half[0], 0.0, z])
        pads.append({
            "name": name,
            "body": body,
            "replaces_collision_mesh": mesh,
            "type": "box",
            "pos_local_m": [round(float(v), 8) for v in body_rot.T @ (center_world - data.xpos[body_id])],
            "rpy_deg": [round(v, 6) + 0.0 for v in rpy_degrees(body_rot.T @ site_rot)],
            "half_size_m": list(half),
            "visible": True,
            "rgba": [0.10, 0.80, 1.0, 0.55],
            "friction": list(args.friction),
        })

    print(f"gripper angle for a {args.object_width * 1000:.1f} mm gap: {grip_angle:.4f} rad")
    text = json.dumps(pads, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
