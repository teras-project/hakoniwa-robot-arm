#!/usr/bin/env python3
"""Run the excavator demo in safe phases: drive, stop, then operate the arm."""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_DIR.parents[2]


def parse_args():
    parser = argparse.ArgumentParser(description="Run the staged excavator demo")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--drive", required=True, type=Path)
    parser.add_argument("--trajectory", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    drive_sender = REPOSITORY_ROOT / "tools/control/send_twist_sequence.py"
    arm_sender = REPOSITORY_ROOT / "tools/control/send_joint_trajectory.py"
    command = [
        sys.executable,
        str(drive_sender),
        str(args.manifest.resolve()),
        "--sequence",
        str(args.drive.resolve()),
    ]
    print("[INFO] Excavator demo phase 1/3: crawler travel", flush=True)
    child = subprocess.Popen(command)
    stopping = False

    def terminate_child(_signum, _frame):
        nonlocal stopping
        stopping = True
        if child.poll() is None:
            child.terminate()

    signal.signal(signal.SIGTERM, terminate_child)
    signal.signal(signal.SIGINT, terminate_child)
    result = child.wait()
    if result != 0:
        print(f"[ERROR] crawler phase failed with rc={result}", flush=True)
        return result

    print("[INFO] Excavator demo phase 2/3: destination reached and stopped", flush=True)
    print("[INFO] Excavator demo phase 3/3: arm operation", flush=True)
    child = subprocess.Popen(
        [
            sys.executable,
            str(arm_sender),
            str(args.manifest.resolve()),
            "--trajectory",
            str(args.trajectory.resolve()),
        ]
    )
    result = child.wait()
    if result != 0:
        print(f"[ERROR] arm phase failed with rc={result}", flush=True)
        return result

    # Keep only this connection-free operator alive for Launcher lifecycle.
    # The short-lived SHM sender must exit so a PS4/manual adapter can call
    # hakopy.init_for_external() later without contending for the master lock.
    print("[INFO] Auto demo complete; waiting for Launcher termination", flush=True)
    while not stopping:
        time.sleep(0.2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
