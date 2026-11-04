from __future__ import annotations

import argparse
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState

try:
    from rclpy.exceptions import RCLError
except ImportError:  # ROS 2 Humble does not export RCLError from rclpy.exceptions.
    from rclpy._rclpy_pybind11 import RCLError


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor Hakoniwa arm joint states")
    parser.add_argument("--topic", default="/joint_states_robot")
    parser.add_argument("--interval", type=float, default=1.0, help="minimum seconds between log lines")
    parser.add_argument(
        "--once",
        action="store_true",
        help="exit after receiving the first JointState message",
    )
    args = parser.parse_args()
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error("--interval must be a positive finite number")
    rclpy.init()
    node = Node("hakoniwa_arm_joint_state_monitor")
    last_log = -math.inf

    def receive(message: JointState) -> None:
        nonlocal last_log
        now = time.monotonic()
        if not args.once and now - last_log < args.interval:
            return
        last_log = now
        values = ", ".join(
            f"{name}={position:.3f}" for name, position in zip(message.name, message.position)
        )
        node.get_logger().info(values or "empty JointState")
        if args.once:
            rclpy.shutdown()

    qos = QoSProfile(
        history=HistoryPolicy.KEEP_LAST,
        depth=10,
        reliability=ReliabilityPolicy.BEST_EFFORT,
        durability=DurabilityPolicy.VOLATILE,
    )
    node.create_subscription(JointState, args.topic, receive, qos)
    node.get_logger().info(f"monitoring {args.topic}")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except RCLError:
        # Humble can report an invalid wait set after its SIGINT handler has
        # already shut down the context. Treat only that shutdown path as a
        # normal Ctrl+C exit; preserve unrelated ROS errors.
        if rclpy.ok():
            raise
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
