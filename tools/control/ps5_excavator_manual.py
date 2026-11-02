#!/usr/bin/env python3
"""Map a PS5 controller to the Excavator Manual PDU contract."""

from __future__ import annotations

import argparse
import json
import math
import signal
import time
from pathlib import Path

import hakopy
from hakoniwa_pdu.impl.shm_communication_service import ShmCommunicationService
from hakoniwa_pdu.pdu_manager import PduManager
from hakoniwa_pdu.pdu_msgs.geometry_msgs.pdu_conv_Twist import py_to_pdu_Twist
from hakoniwa_pdu.pdu_msgs.geometry_msgs.pdu_pytype_Twist import Twist
from hakoniwa_pdu.pdu_msgs.std_msgs.pdu_conv_Float64MultiArray import py_to_pdu_Float64MultiArray
from hakoniwa_pdu.pdu_msgs.std_msgs.pdu_pytype_Float64MultiArray import Float64MultiArray


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_contract(manifest_path: Path):
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    component = next(item for item in manifest["components"] if item["id"] == "excavator_controller")
    controller = load_json((manifest_path.parent / component["config"]).resolve())["spec"]
    return (
        (manifest_path.parent / manifest["pdu_def"]).resolve(),
        component["pdu_robot"],
        controller["manual_joint_velocity_pdu"],
        controller["manual_cmd_vel_pdu"],
        controller["manual_joint_velocity_limits_rad_s"],
    )


def shaped_axis(joystick, spec, deadzone: float, expo: float) -> float:
    value = float(joystick.get_axis(int(spec["index"])))
    if spec.get("inverse", False):
        value = -value
    magnitude = abs(value)
    if magnitude <= deadzone:
        return 0.0
    normalized = min(1.0, (magnitude - deadzone) / (1.0 - deadzone))
    shaped = (1.0 - expo) * normalized + expo * normalized**3
    return math.copysign(shaped, value)


def joint_payload(values):
    message = Float64MultiArray()
    message.data = [float(value) for value in values]
    return bytearray(py_to_pdu_Float64MultiArray(message))


def twist_payload(linear_x: float, angular_z: float):
    message = Twist()
    message.linear.x = float(linear_x)
    message.angular.z = float(angular_z)
    return bytearray(py_to_pdu_Twist(message))


def main() -> int:
    parser = argparse.ArgumentParser(description="PS5 excavator Manual Controller")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--index", default=0, type=int)
    args = parser.parse_args()

    try:
        import pygame
    except ImportError:
        print("[ERROR] pygame is required; run tools/install-ps5-controller.bash")
        return 2

    try:
        pdu_def, robot, joint_channel, base_channel, joint_limits = resolve_contract(args.manifest)
        mapping = load_json(args.mapping.resolve())
        rate_hz = float(mapping.get("send_rate_hz", 20.0))
        deadzone = float(mapping.get("deadzone", 0.10))
        expo = float(mapping.get("expo", 0.35))
        if rate_hz <= 0.0 or not 0.0 <= deadzone < 1.0 or not 0.0 <= expo <= 1.0:
            raise ValueError("rate, deadzone, or expo is invalid")
    except (OSError, KeyError, StopIteration, TypeError, ValueError) as error:
        print(f"[ERROR] Invalid PS5 mapping: {error}")
        return 2

    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() <= args.index:
        print(f"[ERROR] controller index {args.index} is not connected")
        return 1
    joystick = pygame.joystick.Joystick(args.index)
    joystick.init()
    print(
        f"[INFO] PS5 controller: {joystick.get_name()} "
        f"axes={joystick.get_numaxes()} buttons={joystick.get_numbuttons()}",
        flush=True,
    )
    print("[INFO] Hold L1 to operate; hold R1 for stick/bucket bank; Options quits.", flush=True)

    manager = PduManager()
    manager.initialize(config_path=str(pdu_def), comm_service=ShmCommunicationService())
    manager.start_service_nowait()
    stopping = False

    def request_stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    try:
        if not hakopy.init_for_external():
            print("[ERROR] init_for_external() failed")
            return 1
        manager.run_nowait()
        interval = 1.0 / rate_hz
        last_enabled = False
        last_trace_time = 0.0
        while not stopping:
            # Drain SDL's event queue on every cycle.  DualSense controllers
            # generate frequent motion events; merely pumping the queue can
            # eventually leave it full and make later stick input appear
            # unresponsive.
            pygame.event.get()
            buttons = mapping["buttons"]
            if joystick.get_button(int(buttons["quit"])):
                break
            enabled = bool(joystick.get_button(int(buttons["deadman"])))
            if enabled:
                axes = mapping["axes"]
                linear = shaped_axis(joystick, axes["base_linear"], deadzone, expo) * float(mapping["base_limits"]["linear_m_s"])
                angular = shaped_axis(joystick, axes["base_angular"], deadzone, expo) * float(mapping["base_limits"]["angular_rad_s"])
                right_x = shaped_axis(joystick, axes["right_x"], deadzone, expo)
                right_y = shaped_axis(joystick, axes["right_y"], deadzone, expo)
                velocities = [0.0] * len(joint_limits)
                if joystick.get_button(int(buttons["arm_bank_2"])):
                    velocities[2] = right_y * float(joint_limits[2])
                    velocities[3] = right_x * float(joint_limits[3])
                    bank = "stick/bucket"
                else:
                    velocities[0] = right_x * float(joint_limits[0])
                    velocities[1] = right_y * float(joint_limits[1])
                    bank = "swing/boom"
                if not manager.flush_pdu_raw_data_nowait(robot, joint_channel, joint_payload(velocities)) or not manager.flush_pdu_raw_data_nowait(robot, base_channel, twist_payload(linear, angular)):
                    print("[ERROR] failed to send PS5 manual command")
                    return 1
                now = time.monotonic()
                if now - last_trace_time >= 1.0 and (
                    abs(linear) > 1.0e-3
                    or abs(angular) > 1.0e-3
                    or any(abs(value) > 1.0e-3 for value in velocities)
                ):
                    print(
                        "[INFO] PS5 command: "
                        f"linear={linear:.3f} angular={angular:.3f} "
                        f"joint_velocity={[round(value, 3) for value in velocities]}",
                        flush=True,
                    )
                    last_trace_time = now
                if not last_enabled:
                    print(f"[INFO] deadman ON; arm bank={bank}", flush=True)
            elif last_enabled:
                manager.flush_pdu_raw_data_nowait(robot, joint_channel, joint_payload([0.0] * len(joint_limits)))
                manager.flush_pdu_raw_data_nowait(robot, base_channel, twist_payload(0.0, 0.0))
                print("[INFO] deadman OFF; controller timeout will stop and hold", flush=True)
            last_enabled = enabled
            time.sleep(interval)
        return 0
    finally:
        manager.stop_service_nowait()
        pygame.joystick.quit()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
