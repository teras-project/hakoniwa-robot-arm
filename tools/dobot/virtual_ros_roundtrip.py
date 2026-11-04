"""Exercise official Dobot services against an isolated virtual-only ROS graph."""

import argparse
import json
import math
import time

import rclpy
from dobot_msgs_v4 import srv


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-virtual", action="store_true",
                        help="Confirm that this ROS domain has no real Dobot driver")
    args = parser.parse_args()
    if not args.confirm_virtual:
        parser.error("Pass --confirm-virtual after checking the ROS graph")

    rclpy.init()
    node = rclpy.create_node("dobot_virtual_roundtrip")
    enabled = False
    try:
        for _ in range(50):
            names = {name for name, _ in node.get_node_names_and_namespaces()}
            if "dobot_virtual_services" in names:
                break
            time.sleep(.1)
        if ("dobot_virtual_services" not in names
                or names & {"dobot_real_driver", "dobot_twin_router"}):
            raise RuntimeError(f"Not a virtual-only ROS graph: {sorted(names)}")

        clients = {}

        def call(name, **fields):
            kind = getattr(srv, name)
            if name not in clients:
                clients[name] = node.create_client(
                    kind, f"/dobot_bringup_ros2/srv/{name}")
            client = clients[name]
            if not client.wait_for_service(timeout_sec=5):
                raise RuntimeError(f"{name} service not ready")
            request = kind.Request()
            for field, value in fields.items():
                setattr(request, field, value)
            future = client.call_async(request)
            rclpy.spin_until_future_complete(node, future, timeout_sec=5)
            if not future.done():
                raise TimeoutError(f"{name} response timed out")
            if future.exception() is not None:
                raise RuntimeError(f"{name} failed") from future.exception()
            return future.result()

        def angles():
            response = call("GetAngle")
            if response.res != 0:
                raise RuntimeError(f"GetAngle rejected: {response.res}")
            joints = json.loads(response.robot_return.replace("{", "[").replace("}", "]"))
            if len(joints) != 6 or not all(math.isfinite(value) for value in joints):
                raise RuntimeError(f"Invalid joint angles: {joints}")
            return joints

        initial_angles = angles()
        initial = initial_angles[0]
        initial_mode = call("RobotMode")
        if abs(initial) > 10 or initial_mode.res != 0 or initial_mode.robot_return != "{4}":
            raise RuntimeError("Unexpected initial posture or mode; refusing motion")
        target = initial + 5.
        motion = dict(zip("abcdef", initial_angles))
        motion["a"] = target
        for name in ("RequestControl", "ClearError"):
            if call(name).res != 0:
                raise RuntimeError(f"{name} rejected")
        error_id = call("GetErrorID")
        if error_id.res != 0 or error_id.robot_return != "{[]}":
            raise RuntimeError("Unexpected virtual error state")
        if call("ServoJ", **motion, param_value=["t=2"]).res == 0:
            raise RuntimeError("ServoJ accepted a command while disabled")

        if call("EnableRobot").res != 0:
            raise RuntimeError("EnableRobot rejected")
        enabled = True
        if call("ServoJ", **motion, param_value=["t=2"]).res != 0:
            raise RuntimeError("ServoJ rejected")
        time.sleep(.8)
        middle = angles()[0]
        if not initial + 1. < middle < initial + 4.:
            raise RuntimeError(f"Physics did not advance without a request: {middle}")
        if call("Stop").res != 0:
            raise RuntimeError("Stop rejected")
        stopped = angles()[0]
        time.sleep(.7)
        held = angles()[0]
        stopped_mode = call("RobotMode")
        if (abs(held - stopped) >= .2 or stopped_mode.res != 0
                or stopped_mode.robot_return != "{5}"):
            raise RuntimeError(f"Stop did not hold position: {stopped} -> {held}")
        if call("ServoJ", **motion, param_value=["t=1"]).res != 0:
            raise RuntimeError("ServoJ after Stop rejected")
        immediately = angles()[0]
        if immediately >= target - .5:
            raise RuntimeError("ServoJ acknowledgment cannot be distinguished from arrival")
        time.sleep(1.3)
        arrived = angles()[0]
        if abs(arrived - target) >= .2:
            raise RuntimeError(f"Did not arrive at {target} degrees: {arrived}")
        if call("SpeedFactor", ratio=10).res != 0:
            raise RuntimeError("SpeedFactor rejected")
        if call("DO", index=1, status=1, time=500).res != 0:
            raise RuntimeError("DO rejected")
        demo_first = dict(zip("abcdef", [50., -8., 0., 0., 0., 0.]))
        demo_second = dict(zip("abcdef", [0., -8., 0., 0., 0., 0.]))
        for motion in (demo_first, demo_second):
            if call("MovJ", mode=True, **motion).res != 0:
                raise RuntimeError(f"MovJ rejected: {motion}")
        time.sleep(4.)
        demo_mid = angles()[0]
        if not 12. < demo_mid < 42.:
            raise RuntimeError(f"First queued MovJ did not move: {demo_mid}")
        time.sleep(18.)
        demo_final = angles()
        if abs(demo_final[0]) >= .2 or abs(demo_final[1] + 8.) >= .2:
            raise RuntimeError(f"Queued MovJ commands did not finish in order: {demo_final}")
        if call("MovL", mode=False).res == 0:
            raise RuntimeError("Unsupported Cartesian MovL was accepted")
        if call("MovL", mode=True, a=3., b=-8.).res != 0:
            raise RuntimeError("Joint-target MovL rejected")
        time.sleep(2.)
        if abs(angles()[0] - 3.) >= .2:
            raise RuntimeError("Joint-target MovL did not reach target")
    finally:
        try:
            if enabled:
                response = call("DisableRobot")
                if response.res != 0:
                    raise RuntimeError(f"DisableRobot rejected: {response.res}")
        finally:
            node.destroy_node()
            rclpy.shutdown()

    print(json.dumps({"initial_deg": initial, "mid_deg": middle,
                      "stop_deg": stopped, "held_deg": held,
                      "after_ack_deg": immediately, "target_deg": target,
                      "arrived_deg": arrived, "demo_mid_deg": demo_mid,
                      "demo_final_deg": demo_final,
                      "result": "PASS"}, indent=2))


if __name__ == "__main__":
    main()
