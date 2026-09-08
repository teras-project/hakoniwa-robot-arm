import argparse
import json
import signal
import time
from pathlib import Path

import hakopy
from hakoniwa_pdu.impl.shm_communication_service import ShmCommunicationService
from hakoniwa_pdu.pdu_manager import PduManager
from hakoniwa_pdu.pdu_msgs.trajectory_msgs.pdu_conv_JointTrajectory import (
    py_to_pdu_JointTrajectory,
)
from hakoniwa_pdu.pdu_msgs.trajectory_msgs.pdu_pytype_JointTrajectory import (
    JointTrajectory,
)
from hakoniwa_pdu.pdu_msgs.trajectory_msgs.pdu_pytype_JointTrajectoryPoint import (
    JointTrajectoryPoint,
)


PACK_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = PACK_ROOT / "recipes/fr5/asset-manifest.json"


def load_json(path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def resolve_manifest_runtime(manifest_path):
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    manifest_dir = manifest_path.parent

    try:
        trajectory_component = next(
            component
            for component in manifest["components"]
            if component.get("id") == "joint_actuator"
            or component.get("type") == "joint_trajectory_controller"
        )
    except (KeyError, StopIteration) as error:
        raise ValueError(
            "asset manifest must contain a trajectory actuator or controller"
        ) from error

    pdu_def_path = (manifest_dir / manifest["pdu_def"]).resolve()
    actuator_config_path = (
        manifest_dir / trajectory_component["config"]
    ).resolve()
    actuator_config = load_json(actuator_config_path)

    robot_name = trajectory_component.get("pdu_robot", manifest["name"])
    if trajectory_component.get("type") == "joint_trajectory_controller":
        channel_name = actuator_config["input"]["pdu_name"]
    else:
        channel_name = actuator_config["pdu_config"]["pdu_name"]

    return manifest_path, pdu_def_path, robot_name, channel_name


def build_trajectory_points(waypoints, times):
    """
    Position control is currently used. Velocity, acceleration, and effort
    arrays are retained as zero-filled JointTrajectory fields.
    """
    if len(waypoints) != len(times):
        raise ValueError("waypoints and times must have the same length")

    points = []
    for positions, time_from_start in zip(waypoints, times):
        point = JointTrajectoryPoint()
        point.positions = positions
        point.velocities = [0.0] * len(positions)
        point.accelerations = [0.0] * len(positions)
        point.effort = [0.0] * len(positions)

        seconds = int(time_from_start)
        nanoseconds = round((time_from_start - seconds) * 1e9)
        if nanoseconds == 1_000_000_000:
            seconds += 1
            nanoseconds = 0
        point.time_from_start.sec = seconds
        point.time_from_start.nanosec = nanoseconds
        points.append(point)

    return points


def parse_args():
    parser = argparse.ArgumentParser(description="Send a manifest-driven robot-arm demo trajectory")
    parser.add_argument(
        "--trajectory",
        required=True,
        type=Path,
        help="JSON file containing joint_names and trajectory points",
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="asset manifest (default: recipes/fr5/asset-manifest.json)",
    )
    parser.add_argument(
        "--keep-alive",
        action="store_true",
        help="remain alive after sending so Launcher owns the demo lifecycle",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    manifest_path = args.manifest
    if not manifest_path.exists():
        print(f"[ERROR] Asset manifest not found: '{manifest_path}'")
        return 1

    try:
        (
            manifest_path,
            pdu_def_path,
            robot_name,
            channel_name,
        ) = resolve_manifest_runtime(manifest_path)
        trajectory_spec = load_json(args.trajectory.resolve())
        joint_names = trajectory_spec["joint_names"]
        point_specs = trajectory_spec["points"]
        waypoints = [point["positions"] for point in point_specs]
        times = [point["time_from_start"] for point in point_specs]
        if not joint_names or not point_specs:
            raise ValueError("trajectory must contain joint_names and at least one point")
        if any(len(positions) != len(joint_names) for positions in waypoints):
            raise ValueError("every trajectory point must match the joint_names length")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"[ERROR] Failed to resolve asset manifest: {error}")
        return 1

    pdu_manager = PduManager()
    pdu_manager.initialize(
        config_path=str(pdu_def_path),
        comm_service=ShmCommunicationService(),
    )
    pdu_manager.start_service_nowait()

    try:
        ret = hakopy.init_for_external()
        if not ret:
            print(f"ERROR: init_for_external() returns {ret}.")
            return 1

        print(f"Asset manifest: {manifest_path}")
        print(f"PDU definition: {pdu_def_path}")
        print(
            f"Preparing to send JointTrajectory to robot '{robot_name}' "
            f"on channel '{channel_name}'..."
        )

        trajectory = JointTrajectory()
        trajectory.header.stamp.sec = int(time.time())
        trajectory.header.stamp.nanosec = 0
        trajectory.header.frame_id = "map"

        trajectory.joint_names = joint_names

        trajectory.points = build_trajectory_points(waypoints, times)

        print(f"Trajectory created with {len(trajectory.points)} points.")
        for positions, time_from_start in zip(waypoints, times):
            values = [f"{position:.2f}" for position in positions]
            print(f"  t={time_from_start:.1f}s: {values}")

        pdu_data = py_to_pdu_JointTrajectory(trajectory)

        pdu_manager.run_nowait()
        print("PDU channel is ready. Flushing data...")
        result = pdu_manager.flush_pdu_raw_data_nowait(
            robot_name,
            channel_name,
            pdu_data,
        )

        if result:
            print("Successfully sent JointTrajectory PDU.")
            if args.keep_alive:
                stopping = False

                def request_stop(_signum, _frame):
                    nonlocal stopping
                    stopping = True

                signal.signal(signal.SIGTERM, request_stop)
                signal.signal(signal.SIGINT, request_stop)
                print("Launcher lifecycle active; waiting for termination.")
                while not stopping:
                    time.sleep(0.2)
            return 0

        print("Failed to send JointTrajectory PDU.")
        return 1
    finally:
        print("PDU service stopped.")
        pdu_manager.stop_service_nowait()


if __name__ == "__main__":
    raise SystemExit(main())
