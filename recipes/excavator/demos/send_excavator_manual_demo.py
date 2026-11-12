#!/usr/bin/env python3
"""Exercise the controller's Manual interface with repeated deadman commands."""

from __future__ import annotations

import argparse
import json
import signal
import time
from pathlib import Path

import hakopy
from hakoniwa_pdu.impl.shm_communication_service import ShmCommunicationService
from hakoniwa_pdu.pdu_manager import PduManager
from hakoniwa_pdu.pdu_msgs.geometry_msgs.pdu_conv_Twist import py_to_pdu_Twist
from hakoniwa_pdu.pdu_msgs.geometry_msgs.pdu_pytype_Twist import Twist
from hakoniwa_pdu.pdu_msgs.std_msgs.pdu_conv_Float64MultiArray import (
    py_to_pdu_Float64MultiArray,
)
from hakoniwa_pdu.pdu_msgs.std_msgs.pdu_pytype_Float64MultiArray import (
    Float64MultiArray,
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_contract(manifest_path: Path):
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    component = next(
        item for item in manifest["components"] if item["id"] == "excavator_controller"
    )
    config = load_json((manifest_path.parent / component["config"]).resolve())
    spec = config["spec"]
    return (
        (manifest_path.parent / manifest["pdu_def"]).resolve(),
        component["pdu_robot"],
        spec["manual_joint_velocity_pdu"],
        spec["manual_cmd_vel_pdu"],
        len(spec["manual_joint_actuator_components"]),
    )


def joint_payload(values: list[float]) -> bytearray:
    message = Float64MultiArray()
    message.data = [float(value) for value in values]
    return bytearray(py_to_pdu_Float64MultiArray(message))


def twist_payload(linear_x: float, angular_z: float) -> bytearray:
    message = Twist()
    message.linear.x = float(linear_x)
    message.angular.z = float(angular_z)
    return bytearray(py_to_pdu_Twist(message))


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a manual excavator jog demo")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--sequence", required=True, type=Path)
    parser.add_argument("--keep-alive", action="store_true")
    args = parser.parse_args()
    try:
        pdu_def, robot, joint_channel, base_channel, joint_count = resolve_contract(
            args.manifest
        )
        sequence = load_json(args.sequence.resolve())
        rate_hz = float(sequence.get("send_rate_hz", 20.0))
        commands = sequence["commands"]
        if rate_hz <= 0.0 or not commands:
            raise ValueError("send_rate_hz and commands must be non-empty")
        for command in commands:
            if len(command.get("joint_velocity_rad_s", [])) != joint_count:
                raise ValueError(f"every command requires {joint_count} joint velocities")
    except (OSError, KeyError, StopIteration, TypeError, ValueError) as error:
        print(f"[ERROR] Invalid manual demo: {error}")
        return 1

    manager = PduManager()
    manager.initialize(config_path=str(pdu_def), comm_service=ShmCommunicationService())
    manager.start_service_nowait()
    stopping = False

    def stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        if not hakopy.init_for_external():
            print("[ERROR] init_for_external() failed")
            return 1
        manager.run_nowait()
        interval = 1.0 / rate_hz
        for index, command in enumerate(commands):
            velocities = command["joint_velocity_rad_s"]
            linear_x = float(command.get("linear_x", 0.0))
            angular_z = float(command.get("angular_z", 0.0))
            deadline = time.monotonic() + float(command["duration_sec"])
            print(
                f"Manual command[{index}]: joints={velocities} "
                f"linear.x={linear_x:.2f} angular.z={angular_z:.2f}",
                flush=True,
            )
            while not stopping and time.monotonic() < deadline:
                if not manager.flush_pdu_raw_data_nowait(
                    robot, joint_channel, joint_payload(velocities)
                ) or not manager.flush_pdu_raw_data_nowait(
                    robot, base_channel, twist_payload(linear_x, angular_z)
                ):
                    print("[ERROR] Failed to send manual command")
                    return 1
                time.sleep(interval)
            if stopping:
                break
        manager.flush_pdu_raw_data_nowait(
            robot, joint_channel, joint_payload([0.0] * joint_count)
        )
        manager.flush_pdu_raw_data_nowait(
            robot, base_channel, twist_payload(0.0, 0.0)
        )
        print("Manual sequence completed; controller timeout will hold and stop.")
        while args.keep_alive and not stopping:
            time.sleep(0.2)
        return 0
    finally:
        manager.stop_service_nowait()


if __name__ == "__main__":
    raise SystemExit(main())
