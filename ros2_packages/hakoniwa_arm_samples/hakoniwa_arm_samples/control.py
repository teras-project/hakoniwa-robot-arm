from __future__ import annotations

import argparse
import math
import time

import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Publish a robot-independent joint trajectory")
    result.add_argument("--topic", default="/joint_trajectory")
    result.add_argument("--joints", type=int, default=6)
    result.add_argument(
        "--joint-names",
        nargs="+",
        help="explicit joint names in trajectory order (overrides --joints)",
    )
    result.add_argument("--amplitude", type=float, default=0.35)
    result.add_argument("--duration", type=float, default=3.0)
    return result


def main() -> None:
    args = parser().parse_args()
    joint_names = args.joint_names or [
        f"joint{index}" for index in range(1, args.joints + 1)
    ]
    if not joint_names:
        raise SystemExit("at least one joint is required")
    rclpy.init()
    node = Node("hakoniwa_arm_trajectory_sample")
    publisher = node.create_publisher(JointTrajectory, args.topic, 10)
    message = JointTrajectory()
    message.joint_names = joint_names
    for phase in (0.0, 1.0, 2.0, 3.0):
        point = JointTrajectoryPoint()
        point.positions = [
            args.amplitude * math.sin(phase + index * 0.35)
            for index in range(len(joint_names))
        ]
        seconds = phase * args.duration
        point.time_from_start.sec = int(seconds)
        point.time_from_start.nanosec = int((seconds - int(seconds)) * 1_000_000_000)
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
