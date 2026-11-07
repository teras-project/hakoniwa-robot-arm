#!/usr/bin/env python3
"""Drive repeated one-point JointTrajectory input from a pygame gamepad."""

from __future__ import annotations

import argparse
import json
import platform
import re
import signal
import sys
import time
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PACK_ROOT / "tools" / "lib"))

import hakopy
from hakoniwa_pdu.impl.shm_communication_service import ShmCommunicationService
from hakoniwa_pdu.pdu_manager import PduManager
from hakoniwa_pdu.pdu_msgs.sensor_msgs.pdu_conv_JointState import (
    pdu_to_py_JointState,
)
from hakoniwa_pdu.pdu_msgs.trajectory_msgs.pdu_conv_JointTrajectory import (
    py_to_pdu_JointTrajectory,
)
from hakoniwa_pdu.pdu_msgs.trajectory_msgs.pdu_pytype_JointTrajectory import (
    JointTrajectory,
)
from hakoniwa_pdu.pdu_msgs.trajectory_msgs.pdu_pytype_JointTrajectoryPoint import (
    JointTrajectoryPoint,
)

from hakoniwa_robot_arm.controllers.gamepad import normalize, validate_device
from hakoniwa_robot_arm.controllers.manual_jog import ManualJogController


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_contract(manifest_path: Path):
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    manifest_dir = manifest_path.parent
    trajectory = next(
        component
        for component in manifest["components"]
        if component["type"] == "joint_trajectory_controller"
    )
    joint_state = next(
        component
        for component in manifest["components"]
        if component["type"] == "joint_state"
    )
    trajectory_config = load_json((manifest_dir / trajectory["config"]).resolve())
    state_config = load_json((manifest_dir / joint_state["config"]).resolve())
    components = {component["id"]: component for component in manifest["components"]}
    joint_limits = {}
    for binding in trajectory_config["joints"]:
        actuator = components[binding["actuator"]]
        actuator_config = load_json((manifest_dir / actuator["config"]).resolve())
        limit = actuator_config["spec"]["limit"]
        joint_limits[binding["name"]] = (
            float(limit["lower"]),
            float(limit["upper"]),
        )
    command_channel = trajectory_config["input"]["pdu_name"]
    return (
        (manifest_dir / manifest["pdu_def"]).resolve(),
        trajectory.get("pdu_robot", manifest["name"]),
        command_channel,
        joint_state.get("pdu_robot", manifest["name"]),
        state_config["pdu_config"]["pdu_name"],
        joint_limits,
    )


def read_joint_positions(
    manager: PduManager,
    robot: str,
    channel: str,
    expected_names: tuple[str, ...],
):
    raw = manager.read_pdu_raw_data(robot, channel)
    if raw is None:
        return None
    try:
        message = pdu_to_py_JointState(raw)
    except (ValueError, IndexError):
        return None
    if len(message.name) != len(message.position):
        return None
    positions = dict(zip(message.name, message.position))
    if set(positions) != set(expected_names):
        return None
    return {name: float(positions[name]) for name in expected_names}


def trajectory_payload(joint_names: tuple[str, ...], positions: tuple[float, ...]):
    message = JointTrajectory()
    now = time.time()
    message.header.stamp.sec = int(now)
    message.header.stamp.nanosec = int((now - int(now)) * 1.0e9)
    message.header.frame_id = ""
    message.joint_names = list(joint_names)
    point = JointTrajectoryPoint()
    point.positions = list(positions)
    point.velocities = [0.0] * len(positions)
    point.accelerations = [0.0] * len(positions)
    point.effort = [0.0] * len(positions)
    point.time_from_start.sec = 0
    point.time_from_start.nanosec = 0
    message.points = [point]
    return bytearray(py_to_pdu_JointTrajectory(message))


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="JointTrajectory runtime diagnostic driven by a pygame gamepad"
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--device-profile", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--index", default=0, type=int)
    parser.add_argument("--joint-state-timeout-sec", default=10.0, type=float)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        import pygame
    except ImportError:
        print("[ERROR] pygame is required; run tools/install-ps5-controller.bash")
        return 2

    try:
        (
            pdu_def,
            command_robot,
            command_channel,
            state_robot,
            state_channel,
            joint_limits,
        ) = resolve_contract(args.manifest)
        device_profile = load_json(args.device_profile.resolve())
        mapping = load_json(args.mapping.resolve())
        manual = ManualJogController(mapping, joint_limits)
        rate_hz = float(
            mapping.get("input", {}).get(
                "update_rate_hz", mapping["spec"].get("send_rate_hz", 20.0)
            )
        )
        if rate_hz <= 0.0 or args.joint_state_timeout_sec <= 0.0:
            raise ValueError("send rate and JointState timeout must be positive")
    except (OSError, KeyError, StopIteration, TypeError, ValueError) as error:
        print(f"[ERROR] Invalid arm trajectory diagnostic configuration: {error}")
        return 2

    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() <= args.index:
        print(f"[ERROR] controller index {args.index} is not connected")
        pygame.quit()
        return 1
    joystick = pygame.joystick.Joystick(args.index)
    joystick.init()
    try:
        validate_device(
            device_profile,
            os_name=platform.system(),
            backend="pygame",
            device_name=joystick.get_name(),
            axis_count=joystick.get_numaxes(),
            button_count=joystick.get_numbuttons(),
        )
    except (KeyError, TypeError, ValueError, re.error) as error:
        print(f"[ERROR] Connected controller does not match device profile: {error}")
        pygame.quit()
        return 2

    print(
        f"[INFO] pygame controller: {joystick.get_name()} "
        f"axes={joystick.get_numaxes()} buttons={joystick.get_numbuttons()}",
        flush=True,
    )

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
        if not manager.run_nowait():
            print("[ERROR] PDU manager failed to start")
            return 1

        joint_names = tuple(joint_limits)
        deadline = time.monotonic() + args.joint_state_timeout_sec
        positions = None
        while not stopping and time.monotonic() < deadline:
            positions = read_joint_positions(
                manager, state_robot, state_channel, joint_names
            )
            if positions is not None:
                break
            time.sleep(0.05)
        if positions is None:
            print("[ERROR] Timed out waiting for a complete joint_states PDU")
            return 1

        spec = mapping["spec"]
        interval = 1.0 / rate_hz
        last_time = time.monotonic()
        last_bank = None
        was_enabled = False
        consecutive_send_failures = 0
        max_consecutive_send_failures = max(3, int(rate_hz))
        print(
            "[INFO] Hold L1 to jog. Default=j1/j2, R1=j3/j4, "
            "Triangle+left stick=j5/j6, Options=quit.",
            flush=True,
        )
        while not stopping:
            pygame.event.get()
            state = normalize(joystick, device_profile)
            if state.buttons.get(spec["quit_button"], False):
                break

            # SHM communication has no background receive loop. Refresh the
            # local cache so a new deadman session starts from the latest pose.
            manager.run_nowait()
            latest = read_joint_positions(
                manager, state_robot, state_channel, joint_names
            )
            if latest is not None:
                positions = latest
            now = time.monotonic()
            delta = min(0.1, max(1.0e-6, now - last_time))
            last_time = now
            try:
                result = manual.update(state, positions, delta)
            except ValueError as error:
                print(f"[WARN] Manual input rejected: {error}", flush=True)
                result = None

            if result is not None:
                if not manager.flush_pdu_raw_data_nowait(
                    command_robot,
                    command_channel,
                    trajectory_payload(result.joint_names, result.positions),
                ):
                    consecutive_send_failures += 1
                    if consecutive_send_failures == 1:
                        print(
                            "[WARN] JointTrajectory PDU write failed; "
                            "skipping this controller frame",
                            flush=True,
                        )
                    if consecutive_send_failures >= max_consecutive_send_failures:
                        print(
                            "[ERROR] JointTrajectory PDU writes failed for "
                            f"{consecutive_send_failures} consecutive frames"
                        )
                        return 1
                    time.sleep(interval)
                    continue
                if consecutive_send_failures > 0:
                    print(
                        "[INFO] JointTrajectory PDU write recovered after "
                        f"{consecutive_send_failures} failed frame(s)",
                        flush=True,
                    )
                consecutive_send_failures = 0
                if not was_enabled or result.bank_id != last_bank:
                    print(f"[INFO] Manual Enable ON; bank={result.bank_id}", flush=True)
                was_enabled = True
                last_bank = result.bank_id
            elif was_enabled:
                # Replace a potentially obstructed target with the measured
                # pose once. This stops the actuator from continuing to push
                # into a collision after the operator releases the deadman.
                manager.flush_pdu_raw_data_nowait(
                    command_robot,
                    command_channel,
                    trajectory_payload(
                        joint_names,
                        tuple(positions[name] for name in joint_names),
                    ),
                )
                print("[INFO] Manual Enable OFF; sending measured trajectory", flush=True)
                was_enabled = False
                last_bank = None
                consecutive_send_failures = 0
            time.sleep(interval)
        return 0
    finally:
        manager.stop_service_nowait()
        pygame.joystick.quit()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
