from __future__ import annotations

import argparse

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor Hakoniwa arm joint states")
    parser.add_argument("--topic", default="/pdu/joint_states")
    parser.add_argument(
        "--once",
        action="store_true",
        help="exit after receiving the first JointState message",
    )
    args = parser.parse_args()
    rclpy.init()
    node = Node("hakoniwa_arm_joint_state_monitor")

    def receive(message: JointState) -> None:
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
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
