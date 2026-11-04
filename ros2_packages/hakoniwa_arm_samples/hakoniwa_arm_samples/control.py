"""Move a small distance from the observed pose using Dobot's official services."""
from __future__ import annotations

import argparse
import math
import time

import rclpy
from dobot_msgs_v4.srv import EnableRobot, GetAngle, MovJ, RobotMode, SpeedFactor
from rclpy.node import Node


API = "/dobot_bringup_ros2/srv"


def parse_angles(value: str) -> list[float]:
    if not value.startswith("{") or not value.endswith("}"):
        raise ValueError(f"invalid GetAngle response: {value!r}")
    try:
        angles = [float(part) for part in value.strip("{}").split(",")]
    except ValueError as error:
        raise ValueError(f"invalid GetAngle response: {value!r}") from error
    if len(angles) != 6 or not all(math.isfinite(angle) for angle in angles):
        raise ValueError(f"invalid GetAngle response: {value!r}")
    return angles


def call(node: Node, kind, name: str, request):
    client = node.create_client(kind, f"{API}/{name}")
    if not client.wait_for_service(timeout_sec=2.0):
        raise RuntimeError(f"{name} service not available")
    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=2.0)
    if not future.done():
        future.cancel()
        raise TimeoutError(f"{name} timed out; command outcome may be unknown, do not retry")
    response = future.result()
    if response is None or response.res != 0:
        raise RuntimeError(f"{name} failed: {response!r}")
    return response


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="enable and move the robot (including a real robot)")
    parser.add_argument("--delta-deg", type=float, default=3.0, help="J1 displacement in degrees (maximum 5)")
    args = parser.parse_args()
    if not math.isfinite(args.delta_deg) or not 0 < abs(args.delta_deg) <= 5:
        parser.error("--delta-deg must be nonzero and within +/-5 degrees")

    rclpy.init()
    node = Node("hakoniwa_arm_control_sample")
    try:
        initial = parse_angles(call(node, GetAngle, "GetAngle", GetAngle.Request()).robot_return)
        target = initial.copy()
        target[0] += args.delta_deg
        if abs(target[0]) > 350:
            raise ValueError(f"J1 target is too close to its limit: {target[0]} degrees")
        node.get_logger().info(f"Current (deg): {initial}; target (deg): {target}")
        if not args.execute:
            node.get_logger().info("Dry run: pass --execute after checking the robot and workspace")
            return
        call(node, EnableRobot, "EnableRobot", EnableRobot.Request())
        speed = SpeedFactor.Request()
        speed.ratio = 10
        call(node, SpeedFactor, "SpeedFactor", speed)
        move = MovJ.Request()
        move.mode = True
        move.a, move.b, move.c, move.d, move.e, move.f = target
        call(node, MovJ, "MovJ", move)
        node.get_logger().info("MovJ accepted; waiting for measured motion to finish")
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            mode = call(node, RobotMode, "RobotMode", RobotMode.Request())
            if mode.robot_return == "{5}":
                actual = parse_angles(call(node, GetAngle, "GetAngle", GetAngle.Request()).robot_return)
                if max(abs(a - b) for a, b in zip(actual, target)) > 1:
                    raise RuntimeError(f"MovJ ended away from target: {actual}")
                node.get_logger().info(f"Reached target (deg): {actual}")
                break
            time.sleep(.5)
        else:
            raise TimeoutError("Motion did not finish in 15s; inspect robot before another command")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
