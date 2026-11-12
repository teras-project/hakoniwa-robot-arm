#!/usr/bin/env python3
"""Replay a manifest-driven geometry_msgs/Twist sequence through SHM."""

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


PACK_ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def resolve_mobile_base(manifest_path: Path):
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    manifest_dir = manifest_path.parent
    try:
        component = next(
            item for item in manifest["components"] if item["id"] == "mobile_base"
        )
    except (KeyError, StopIteration) as error:
        raise ValueError("asset manifest must contain component 'mobile_base'") from error
    config = load_json((manifest_dir / component["config"]).resolve())
    return (
        (manifest_dir / manifest["pdu_def"]).resolve(),
        component.get("pdu_robot", manifest["name"]),
        config["pdu_config"]["pdu_name"],
    )


def make_payload(linear_x: float, angular_z: float) -> bytearray:
    message = Twist()
    message.linear.x = float(linear_x)
    message.angular.z = float(angular_z)
    return bytearray(py_to_pdu_Twist(message))


def parse_args():
    parser = argparse.ArgumentParser(description="Send a mobile-base Twist demo sequence")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--sequence", required=True, type=Path)
    parser.add_argument("--keep-alive", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        pdu_def, robot_name, channel_name = resolve_mobile_base(args.manifest)
        sequence = load_json(args.sequence.resolve())
        rate_hz = float(sequence.get("send_rate_hz", 20.0))
        commands = sequence["commands"]
        if rate_hz <= 0.0 or not commands:
            raise ValueError("send_rate_hz must be positive and commands must not be empty")
        for command in commands:
            if float(command["duration_sec"]) < 0.0:
                raise ValueError("command duration_sec must be non-negative")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"[ERROR] Failed to resolve Twist sequence: {error}")
        return 1

    manager = PduManager()
    manager.initialize(config_path=str(pdu_def), comm_service=ShmCommunicationService())
    manager.start_service_nowait()
    stopping = False

    def request_stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    try:
        if not hakopy.init_for_external():
            print("[ERROR] init_for_external() failed")
            return 1
        manager.run_nowait()
        interval_sec = 1.0 / rate_hz
        print(
            f"Twist sequence started: robot={robot_name} channel={channel_name} "
            f"commands={len(commands)} rate={rate_hz:.1f}Hz"
        )
        for index, command in enumerate(commands):
            linear_x = float(command.get("linear_x", 0.0))
            angular_z = float(command.get("angular_z", 0.0))
            duration_sec = float(command["duration_sec"])
            payload = make_payload(linear_x, angular_z)
            print(
                f"  command[{index}] duration={duration_sec:.1f}s "
                f"linear.x={linear_x:.3f} angular.z={angular_z:.3f}"
            )
            deadline = time.monotonic() + duration_sec
            while not stopping and time.monotonic() < deadline:
                if not manager.flush_pdu_raw_data_nowait(robot_name, channel_name, payload):
                    print("[ERROR] Failed to send Twist PDU")
                    return 1
                time.sleep(interval_sec)
            if stopping:
                break
        manager.flush_pdu_raw_data_nowait(
            robot_name, channel_name, make_payload(0.0, 0.0)
        )
        print("Successfully completed Twist sequence.")
        while args.keep_alive and not stopping:
            time.sleep(0.2)
        return 0
    finally:
        manager.stop_service_nowait()


if __name__ == "__main__":
    raise SystemExit(main())
