#!/usr/bin/env python3
"""Publish a normalized pygame gamepad as a sensor_msgs/Joy PDU."""

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
from hakoniwa_pdu.pdu_msgs.sensor_msgs.pdu_conv_Joy import py_to_pdu_Joy
from hakoniwa_pdu.pdu_msgs.sensor_msgs.pdu_pytype_Joy import Joy

from hakoniwa_robot_arm.controllers.gamepad import (
    NormalizedGamepadState,
    normalize,
    validate_device,
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_contract(manifest_path: Path):
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    component = next(
        item
        for item in manifest["components"]
        if item["type"] == "joy_manual_controller"
    )
    config_path = (manifest_path.parent / component["config"]).resolve()
    config = load_json(config_path)
    input_config = config["input"]
    layout_path = (config_path.parent / config["joy_layout"]).resolve()
    layout = load_json(layout_path)
    return (
        (manifest_path.parent / manifest["pdu_def"]).resolve(),
        component.get("pdu_robot", manifest["name"]),
        input_config["pdu_name"],
        float(input_config["update_rate_hz"]),
        config["spec"]["quit_button"],
        layout_path,
        layout,
    )


def joy_message(state: NormalizedGamepadState, layout: dict, timestamp: float | None = None) -> Joy:
    if layout.get("schema_version") != 1:
        raise ValueError("unsupported logical Joy layout schema_version")
    message = Joy()
    now = time.time() if timestamp is None else timestamp
    message.header.stamp.sec = int(now)
    message.header.stamp.nanosec = int((now - int(now)) * 1.0e9)
    message.header.frame_id = layout["id"]
    message.axes = [float(state.axes.get(name, 0.0)) for name in layout["axes"]]
    message.buttons = [int(bool(state.buttons.get(name, False))) for name in layout["buttons"]]
    return message


def joy_payload(state: NormalizedGamepadState, layout: dict) -> bytearray:
    return bytearray(py_to_pdu_Joy(joy_message(state, layout)))


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Publish a normalized pygame gamepad to the arm Manual Controller"
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--device-profile", required=True, type=Path)
    parser.add_argument("--index", default=0, type=int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        import pygame
    except ImportError:
        print("[ERROR] pygame is required for the gamepad frontend")
        return 2

    try:
        pdu_def, robot, channel, rate_hz, quit_button, _, layout = resolve_contract(
            args.manifest
        )
        device_profile = load_json(args.device_profile.resolve())
        if rate_hz <= 0.0:
            raise ValueError("Joy update rate must be positive")
        if quit_button not in layout["buttons"]:
            raise ValueError("quit_button is not present in the logical Joy layout")
    except (OSError, KeyError, StopIteration, TypeError, ValueError) as error:
        print(f"[ERROR] Invalid arm gamepad configuration: {error}")
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

        interval = 1.0 / rate_hz
        consecutive_send_failures = 0
        max_consecutive_send_failures = max(3, int(rate_hz))
        print("[INFO] Gamepad input is active; configured quit button exits.", flush=True)
        while not stopping:
            pygame.event.get()
            state = normalize(joystick, device_profile)
            if state.buttons.get(quit_button, False):
                break
            if not manager.flush_pdu_raw_data_nowait(
                robot, channel, joy_payload(state, layout)
            ):
                consecutive_send_failures += 1
                if consecutive_send_failures == 1:
                    print("[WARN] Joy PDU write failed; skipping this frame", flush=True)
                if consecutive_send_failures >= max_consecutive_send_failures:
                    print(
                        f"[ERROR] Joy PDU writes failed for "
                        f"{consecutive_send_failures} consecutive frames"
                    )
                    return 1
            else:
                consecutive_send_failures = 0
            time.sleep(interval)
        return 0
    finally:
        manager.stop_service_nowait()
        pygame.joystick.quit()
        pygame.quit()


if __name__ == "__main__":
    raise SystemExit(main())
