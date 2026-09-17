from __future__ import annotations

import argparse
import math
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

from .trajectory_file import load_trajectory_file


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Publish a robot-independent joint trajectory")
    result.add_argument("--topic", default="/joint_trajectory")
    result.add_argument(
        "--trajectory",
        type=Path,
        help="JSON file containing joint_names and trajectory points",
    )
    result.add_argument("--joints", type=int)
    result.add_argument(
        "--joint-names",
        nargs="+",
        help="explicit joint names in trajectory order (overrides --joints)",
    )
    result.add_argument("--amplitude", type=float)
    result.add_argument("--duration", type=float)
    return result


def main() -> None:
    argument_parser = parser()
    args = argument_parser.parse_args()
    generated_options = (
        args.joints,
        args.joint_names,
        args.amplitude,
        args.duration,
    )
    if args.trajectory is not None and any(
        value is not None for value in generated_options
    ):
        argument_parser.error(
            "--trajectory cannot be combined with --joints, --joint-names, "
            "--amplitude, or --duration"
        )

    if args.trajectory is not None:
        try:
            joint_names, point_specs = load_trajectory_file(args.trajectory)
        except ValueError as error:
            argument_parser.error(str(error))
    else:
        joint_count = 6 if args.joints is None else args.joints
        amplitude = 0.35 if args.amplitude is None else args.amplitude
        duration = 3.0 if args.duration is None else args.duration
        joint_names = args.joint_names or [
            f"joint{index}" for index in range(1, joint_count + 1)
        ]
        if not joint_names:
            argument_parser.error("at least one joint is required")
        point_specs = [
            {
                "positions": [
                    amplitude * math.sin(phase + index * 0.35)
                    for index in range(len(joint_names))
                ],
                "time_from_start": phase * duration,
            }
            for phase in (0.0, 1.0, 2.0, 3.0)
        ]

    rclpy.init()
    node = Node("hakoniwa_arm_trajectory_sample")
    publisher = node.create_publisher(JointTrajectory, args.topic, 10)
    message = JointTrajectory()
    message.joint_names = joint_names
    for point_spec in point_specs:
        point = JointTrajectoryPoint()
        point.positions = point_spec["positions"]
        seconds = point_spec["time_from_start"]
        point.time_from_start.sec = int(seconds)
        nanoseconds = round((seconds - int(seconds)) * 1_000_000_000)
        if nanoseconds == 1_000_000_000:
            point.time_from_start.sec += 1
            nanoseconds = 0
        point.time_from_start.nanosec = nanoseconds
        message.points.append(point)

    deadline = time.monotonic() + 2.0
    while publisher.get_subscription_count() == 0 and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    publisher.publish(message)
    node.get_logger().info(
        f"published {len(message.points)} points for {len(joint_names)} joints to {args.topic}"
    )
    rclpy.spin_once(node, timeout_sec=0.2)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
