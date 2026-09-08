#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS_DIR))

from _hakoniwa_composer import (  # noqa: E402
    HakoniwaComposerError,
    arm_root,
    load_foundation_module,
    model_install_dir,
)


RECIPE_ID = ""
ROBOT_ID = ""
ROBOT_LABEL = ""


def select_robot(robot_id: str, robot_label: str) -> None:
    global RECIPE_ID, ROBOT_ID, ROBOT_LABEL
    ROBOT_ID = robot_id
    ROBOT_LABEL = robot_label
    RECIPE_ID = f"{robot_id}-joint-trajectory-control"


class RecipeError(RuntimeError):
    pass


def absolute(path: Path) -> Path:
    return Path(os.path.abspath(path.expanduser()))


def sibling(name: str, env_name: str) -> Path:
    configured = os.environ.get(env_name)
    return absolute(Path(configured) if configured else arm_root().parent / name)


def recipe_file() -> Path:
    return arm_root() / "recipes" / ROBOT_ID / f"{RECIPE_ID}.yaml"


def required(path: Path, label: str) -> Path:
    path = absolute(path)
    if not path.exists():
        raise RecipeError(f"{label} not found: {path}")
    return path


def workspace_and_foundation():
    foundation = load_foundation_module()
    workspace = foundation.resolve_workspace(arm_root(), RECIPE_ID)
    inspection = foundation.inspect_foundation(
        recipe_file(), workspace.install_prefix, validate_core_config=True
    )
    if inspection["status"] != "SATISFIED":
        foundation.print_inspection(inspection, False)
        raise RecipeError(
            "Foundation is not reusable; run "
            "$HAKONIWA_COMPOSER/tools/foundation.py build first"
        )
    return foundation, workspace


def foundation_python(foundation, workspace) -> Path:
    return required(
        foundation.foundation_python_executable(workspace.foundation_python),
        "Foundation Python",
    )


def endpoint_library(prefix: Path) -> Path:
    name = {
        "Darwin": "libhakoniwa_pdu_endpoint_core_callback.dylib",
        "Windows": "hakoniwa_pdu_endpoint_core_callback.dll",
    }.get(platform.system(), "libhakoniwa_pdu_endpoint_core_callback.so")
    candidates = (prefix / "lib" / name, prefix / "bin" / name)
    return absolute(next((candidate for candidate in candidates if candidate.is_file()), candidates[0]))


def runtime_target() -> str:
    return "robot-arm-hakoniwa-asset"


def binary(workspace) -> Path:
    suffix = ".exe" if platform.system() == "Windows" else ""
    return workspace.recipe_root / "build" / "bin" / f"{runtime_target()}{suffix}"


def session_file(workspace) -> Path:
    return workspace.recipe_root / "runtime" / "launcher-session.json"


def environment(foundation, workspace) -> dict[str, str]:
    python = foundation_python(foundation, workspace)
    env = os.environ.copy()
    env.update({
        "HAKONIWA_CORE_ROOT": str(workspace.install_prefix),
        "HAKONIWA_PDU_ENDPOINT_ROOT": str(workspace.install_prefix),
        "HAKONIWA_FOUNDATION_PREFIX": str(workspace.install_prefix),
        "HAKO_CONFIG_PATH": str(workspace.foundation_config / "cpp_core_config.json"),
        "HAKO_PDU_ENDPOINT_SHARED_LIB": str(endpoint_library(workspace.install_prefix)),
        "PYTHON_CMD": str(python),
        "PYTHONUNBUFFERED": "1",
    })
    env["PATH"] = os.pathsep.join(
        [str(python.parent), str(workspace.install_prefix / "bin"), env.get("PATH", "")]
    )
    library_key = "PATH" if platform.system() == "Windows" else (
        "DYLD_LIBRARY_PATH" if platform.system() == "Darwin" else "LD_LIBRARY_PATH"
    )
    env[library_key] = os.pathsep.join(
        [str(workspace.install_prefix / "lib"), env.get(library_key, "")]
    )
    return env


def plant_runtime_ready(log: str) -> bool:
    """Accept the startup markers emitted by supported Robot Runtime releases."""
    return any(
        marker in log
        for marker in (
            "Starting manifest-driven Runtime",
            "Starting Hakoniwa Runner",
        )
    )


def write_json(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def manifest_model_path(manifest: dict) -> Path:
    model = manifest.get("model")
    if not isinstance(model, str) or not model:
        raise RecipeError(f"{ROBOT_LABEL} manifest has no model")
    return model_install_dir(ROBOT_ID) / Path(model).name


def materialize_runtime_manifest(template: Path, workspace) -> Path:
    """Write a workspace-owned manifest with absolute runtime inputs."""
    data = json.loads(template.read_text(encoding="utf-8"))
    template_dir = template.parent
    data["model"] = str(required(manifest_model_path(data), f"{ROBOT_LABEL} forged model"))
    for field in ("pdu_def", "endpoint", "runtime_config"):
        value = data.get(field)
        if isinstance(value, str):
            data[field] = str(required(template_dir / value, f"{ROBOT_LABEL} manifest {field}"))
    for component in data.get("components", []):
        if not isinstance(component, dict):
            continue
        value = component.get("config")
        if isinstance(value, str):
            component["config"] = str(
                required(template_dir / value, f"{ROBOT_LABEL} component config")
            )
    return write_json(workspace.recipe_config / template.name, data)


def materialize_arm_environment() -> None:
    pack = arm_root()
    recipe = pack / "recipes" / ROBOT_ID
    source_manifest = json.loads(
        required(recipe / "asset-manifest.json", f"{ROBOT_LABEL} manifest").read_text(
            encoding="utf-8"
        )
    )
    environment_manifest = json.loads(
        required(
            recipe / "asset-manifest-environment.json",
            f"{ROBOT_LABEL} environment manifest",
        ).read_text(encoding="utf-8")
    )
    source = required(manifest_model_path(source_manifest), f"{ROBOT_LABEL} forged model")
    output = manifest_model_path(environment_manifest)
    generator = required(
        pack / "tools/generate_arm_environment.py",
        "arm environment generator",
    )
    config = required(
        recipe / "config/environment/workspace.json",
        f"{ROBOT_LABEL} environment configuration",
    )
    if run(
        [
            sys.executable,
            str(generator),
            str(source),
            "--config",
            str(config),
            "--output",
            str(output),
        ],
        cwd=pack,
    ) != 0:
        raise RecipeError(f"{ROBOT_LABEL} environment materialization failed")
    print(f"{ROBOT_LABEL} collision environment is up to date.")


def configure(
    headless: bool,
    ros2_tcp: bool = False,
    gamepad_controller: bool = False,
    arm_environment: bool = False,
    realtime_sync_cycle_msec: int = 0,
) -> int:
    if ros2_tcp and gamepad_controller:
        raise RecipeError("--ros2-tcp and --gamepad are exclusive")
    if realtime_sync_cycle_msec < 0:
        raise RecipeError("--realtime-sync-cycle-msec must be >= 0")
    foundation, workspace = workspace_and_foundation()
    foundation.prepare_workspace(workspace)
    python = foundation_python(foundation, workspace)
    if arm_environment:
        materialize_arm_environment()
    manifest_name = "asset-manifest.json"
    if arm_environment:
        manifest_name = "asset-manifest-environment.json"
    manifest_template = required(
        arm_root() / "recipes" / ROBOT_ID / manifest_name,
        f"{ROBOT_LABEL} manifest",
    )
    manifest = materialize_runtime_manifest(manifest_template, workspace)
    sender = required(
        arm_root() / "tools/control/send_joint_trajectory.py",
        "trajectory sender",
    )
    trajectory = required(
        arm_root() / "recipes" / ROBOT_ID / "demo-trajectory.json",
        f"{ROBOT_LABEL} demo trajectory",
    )
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    assets = [
        {
            "name": f"{ROBOT_ID}-plant",
            "activation_timing": "before_start",
            "command": str(binary(workspace)),
            "args": [
                "--manifest",
                str(manifest),
                *(["--no-viewer"] if headless else []),
                *(
                    ["--realtime-sync-cycle-msec", str(realtime_sync_cycle_msec)]
                    if realtime_sync_cycle_msec > 0
                    else []
                ),
            ],
            "delay_sec": 2,
        }
    ]
    if ros2_tcp:
        import ros2_tcp as ros2_tcp_recipe

        config_root = ros2_tcp_recipe.configure(ROBOT_ID, ros2_tcp_recipe.DEFAULT_PORT)
        bridge_binary = required(
            ros2_tcp_recipe.host_bridge_binary(ROBOT_ID),
            "Foundation PDU bridge",
        )
        assets.append({
            "name": f"{ROBOT_ID}-ros2-tcp-bridge",
            "activation_timing": "before_start",
            "command": str(bridge_binary),
            "args": [
                "--config-root", str(config_root),
                "--node-name", "arm_ros2_tcp_node",
                "--asset-name", "Ros2TcpBridge",
                "--delta-time-step-usec", "20000",
            ],
            "depends_on": [f"{ROBOT_ID}-plant"],
            "delay_sec": 1,
        })
    else:
        if gamepad_controller:
            gamepad_sender = required(
                arm_root() / "tools/control/arm_manual.py",
                "robot-arm gamepad input adapter",
            )
            gamepad_args = [
                str(gamepad_sender),
                str(manifest),
                "--device-profile",
                str(required(
                    arm_root() / "profiles/gamepads/dualsense/macos-pygame.json",
                    "DualSense macOS pygame profile",
                )),
            ]
            gamepad_asset_name = f"{ROBOT_ID}-gamepad-controller"
            assets.append({
                "name": gamepad_asset_name,
                "activation_timing": "after_start",
                "command": str(python),
                "args": gamepad_args,
                "depends_on": [f"{ROBOT_ID}-plant"],
                "delay_sec": 1,
            })
        else:
            assets.append({
                "name": f"{ROBOT_ID}-trajectory-sender",
                "activation_timing": "after_start",
                "command": str(python),
                "args": [str(sender), str(manifest), "--trajectory", str(trajectory), "--keep-alive"],
                "depends_on": [f"{ROBOT_ID}-plant"],
                "delay_sec": 1,
            })

    launcher = {
        "version": "0.1",
        "defaults": {
            "cwd": str(arm_root()),
            "stdout": str(workspace.recipe_logs / "${asset}.out"),
            "stderr": str(workspace.recipe_logs / "${asset}.err"),
            "start_grace_sec": 2,
            "delay_sec": 1,
            "env": {
                "set": {
                    "HAKO_CONFIG_PATH": str(workspace.foundation_config / "cpp_core_config.json"),
                    "HAKO_PDU_ENDPOINT_SHARED_LIB": str(endpoint_library(workspace.install_prefix)),
                    "PYTHONUNBUFFERED": "1",
                },
                "prepend": {
                    "lib_path": [str(workspace.install_prefix / "lib")],
                    "PATH": [str(python.parent), str(workspace.install_prefix / "bin")],
                },
            },
        },
        "assets": assets,
    }
    output = write_json(workspace.recipe_config / "launcher.json", launcher)
    print(f"Recipe workspace: {workspace.recipe_root}")
    print(f"Launcher        : {output}")
    print(f"Mode            : {'headless' if headless else 'viewer'}")
    print(f"ROS 2 TCP       : {'enabled' if ros2_tcp else 'disabled'}")
    print(f"Gamepad         : {'enabled' if gamepad_controller else 'disabled'}")
    print(f"Arm environment : {'enabled' if arm_environment else 'disabled'}")
    print(
        "Realtime pacing : "
        + (
            f"{realtime_sync_cycle_msec} ms simulation-time cycle"
            if realtime_sync_cycle_msec > 0
            else "disabled"
        )
    )
    return 0


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> int:
    print("+", subprocess.list2cmdline(command), flush=True)
    return subprocess.run(command, cwd=cwd, env=env, check=False).returncode


def build(mujoco_root: Path, headless: bool) -> int:
    foundation, workspace = workspace_and_foundation()
    required(mujoco_root / "src/CMakeLists.txt", "hakoniwa-mujoco-robots sibling")
    build_dir = workspace.recipe_root / "build"
    configure_command = [
        "cmake", "-S", str(arm_root()), "-B", str(build_dir),
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DHAKONIWA_FOUNDATION_PREFIX={workspace.install_prefix}",
        f"-DHAKONIWA_MUJOCO_ROBOTS_ROOT={mujoco_root}",
        "-DHAKO_USE_THIRDPARTY_HAKONIWA=OFF",
        f"-DHAKO_ARM_ENABLE_VIEWER={'OFF' if headless else 'ON'}",
    ]
    env = environment(foundation, workspace)
    if run(configure_command, cwd=arm_root(), env=env) != 0:
        return 1
    return run(
        ["cmake", "--build", str(build_dir), "--target", runtime_target(), "--parallel", "2"],
        cwd=arm_root(), env=env,
    )


def doctor(mujoco_root: Path) -> int:
    foundation, workspace = workspace_and_foundation()
    python = foundation_python(foundation, workspace)
    manifest_path = arm_root() / "recipes" / ROBOT_ID / "asset-manifest.json"
    manifest_data = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.is_file()
        else {}
    )
    model_value = manifest_data.get("model")
    forged_model = (
        model_install_dir(ROBOT_ID) / Path(model_value).name
        if isinstance(model_value, str) and model_value
        else model_install_dir(ROBOT_ID) / "<missing-model>"
    )
    checks = (
        ("Hakoniwa Composer Foundation engine", True, "reused from configured checkout"),
        ("hakoniwa-mujoco-robots sibling", (mujoco_root / "src/CMakeLists.txt").is_file(), str(mujoco_root)),
        ("Foundation Python", python.is_file(), str(python)),
        ("hako-cmd", (workspace.install_prefix / "bin/hako-cmd").is_file(), str(workspace.install_prefix / "bin/hako-cmd")),
        ("Endpoint core callback", endpoint_library(workspace.install_prefix).is_file(), str(endpoint_library(workspace.install_prefix))),
        ("Core runtime config", (workspace.foundation_config / "cpp_core_config.json").is_file(), str(workspace.foundation_config / "cpp_core_config.json")),
        (f"{ROBOT_LABEL} manifest", manifest_path.is_file(), str(manifest_path)),
        (f"{ROBOT_LABEL} forged model", forged_model.is_file(), str(forged_model)),
        ("Arm runtime", binary(workspace).is_file(), str(binary(workspace))),
        ("generated Launcher", (workspace.recipe_config / "launcher.json").is_file(), str(workspace.recipe_config / "launcher.json")),
    )
    failed = False
    for name, ok, detail in checks:
        print(f"[{'OK' if ok else 'NG'}] {name}: {detail}")
        failed = failed or not ok
    return 1 if failed else 0


def launcher_command(foundation, workspace, operation: str) -> list[str]:
    python = foundation_python(foundation, workspace)
    if operation == "start":
        return [
            str(python), "-m", "hakoniwa_pdu.apps.launcher.hako_launcher",
            str(workspace.recipe_config / "launcher.json"),
            "--background", str(session_file(workspace)),
        ]
    return [
        str(python), "-m", "hakoniwa_pdu.apps.launcher.hako_launcher_ctl",
        operation, str(session_file(workspace)),
    ]


def state(command: list[str], env: dict[str, str]) -> str | None:
    completed = subprocess.run(command, env=env, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return None
    try:
        return json.loads([line for line in completed.stdout.splitlines() if line.strip()][-1]).get("state")
    except (IndexError, json.JSONDecodeError, AttributeError):
        return None


def start() -> int:
    foundation, workspace = workspace_and_foundation()
    required(binary(workspace), "Arm runtime")
    required(workspace.recipe_config / "launcher.json", "generated Launcher")
    session_file(workspace).parent.mkdir(parents=True, exist_ok=True)
    env = environment(foundation, workspace)
    if run(launcher_command(foundation, workspace, "start"), env=env) != 0:
        return 1
    status_command = launcher_command(foundation, workspace, "status")
    plant_log = workspace.recipe_logs / f"{ROBOT_ID}-plant.out"
    sender_log = workspace.recipe_logs / f"{ROBOT_ID}-trajectory-sender.out"
    bridge_log = workspace.recipe_logs / f"{ROBOT_ID}-ros2-tcp-bridge.out"
    launcher = json.loads((workspace.recipe_config / "launcher.json").read_text(encoding="utf-8"))
    asset_names = {asset.get("name") for asset in launcher.get("assets", [])}
    ros2_tcp = f"{ROBOT_ID}-ros2-tcp-bridge" in asset_names
    gamepad_asset_name = (
        f"{ROBOT_ID}-gamepad-controller"
        if f"{ROBOT_ID}-gamepad-controller" in asset_names
        else None
    )
    gamepad_controller_enabled = gamepad_asset_name is not None
    current = None
    for _ in range(40):
        current = state(status_command, env)
        plant = plant_log.read_text(encoding="utf-8", errors="replace") if plant_log.is_file() else ""
        sender = sender_log.read_text(encoding="utf-8", errors="replace") if sender_log.is_file() else ""
        bridge = bridge_log.read_text(encoding="utf-8", errors="replace") if bridge_log.is_file() else ""
        ready_peer = "initializing endpoint container" in bridge if ros2_tcp else "Successfully sent" in sender
        if gamepad_controller_enabled:
            gamepad_log = workspace.recipe_logs / f"{gamepad_asset_name}.out"
            gamepad = gamepad_log.read_text(encoding="utf-8", errors="replace") if gamepad_log.is_file() else ""
            ready_peer = "pygame controller:" in gamepad
        runtime_ready = plant_runtime_ready(plant)
        if current == "RUNNING" and runtime_ready and ready_peer:
            print(f"{ROBOT_LABEL} demo is running in the background.")
            print(f"Session: {session_file(workspace)}")
            print(f"Logs   : {workspace.recipe_logs}")
            return 0
        if current not in (None, "RUNNING"):
            break
        time.sleep(0.5)
    print(f"[NG] {ROBOT_LABEL} runtime is not ready; state={current}, logs={workspace.recipe_logs}", file=sys.stderr)
    return 1


def control(operation: str) -> int:
    foundation, workspace = workspace_and_foundation()
    return run(launcher_command(foundation, workspace, operation), env=environment(foundation, workspace))


def smoke() -> int:
    foundation, workspace = workspace_and_foundation()
    try:
        if start() != 0:
            return 1
        plant_log = workspace.recipe_logs / f"{ROBOT_ID}-plant.out"
        for _ in range(40):
            content = plant_log.read_text(encoding="utf-8", errors="replace") if plant_log.is_file() else ""
            sender_log = workspace.recipe_logs / f"{ROBOT_ID}-trajectory-sender.out"
            sender = (
                sender_log.read_text(encoding="utf-8", errors="replace")
                if sender_log.is_file()
                else ""
            )
            command_observed = "Successfully sent" in sender
            if command_observed:
                time.sleep(1.0)
                content = plant_log.read_text(encoding="utf-8", errors="replace")
                instability_markers = ("simulation is unstable", "Nan, Inf or huge value")
                if any(marker in content for marker in instability_markers):
                    print(f"[NG] MuJoCo numerical instability was observed: {plant_log}", file=sys.stderr)
                    return 1
                print(f"[OK] {ROBOT_LABEL} received the Launcher-managed command input.")
                print(f"[OK] {ROBOT_LABEL} remained numerically stable during the smoke window.")
                return 0
            time.sleep(0.5)
        print(f"[NG] trajectory acceptance was not observed: {plant_log}", file=sys.stderr)
        return 1
    finally:
        run(launcher_command(foundation, workspace, "terminate"), env=environment(foundation, workspace))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=f"Configure and operate the {ROBOT_LABEL} arm Recipe")
    commands = ["configure", "build", "doctor", "start", "status", "stop", "smoke"]
    result.add_argument("command", choices=commands)
    result.add_argument("--headless", action="store_true")
    result.add_argument("--ros2-tcp", action="store_true", help="launch the host SHM/TCP bridge instead of the demo sender")
    result.add_argument(
        "--gamepad", dest="gamepad_controller", action="store_true",
        help="launch the pygame gamepad input adapter instead of the Auto demo")
    result.add_argument(
        "--ps5-controller", dest="gamepad_controller", action="store_true",
        help=argparse.SUPPRESS)
    result.add_argument("--environment", action="store_true", help="select the robot-specific Recipe environment")
    result.add_argument("--realtime-sync-cycle-msec", type=int, default=0, help="reconcile simulation and wall time at this simulation-time interval; 0 disables pacing")
    result.add_argument("--mujoco-root", type=Path, default=sibling("hakoniwa-mujoco-robots", "HAKONIWA_MUJOCO_ROBOTS_ROOT"))
    return result


def main(argv: list[str] | None = None) -> int:
    if not ROBOT_ID or not ROBOT_LABEL:
        raise RuntimeError("select_robot() must be called before arm.main()")
    args = parser().parse_args(argv)
    try:
        if args.command == "configure":
            return configure(
                args.headless,
                args.ros2_tcp,
                args.gamepad_controller,
                args.environment,
                args.realtime_sync_cycle_msec,
            )
        if args.command == "build":
            return build(absolute(args.mujoco_root), args.headless)
        if args.command == "doctor":
            return doctor(absolute(args.mujoco_root))
        if args.command == "start":
            return start()
        if args.command == "smoke":
            return smoke()
        return control("status" if args.command == "status" else "terminate")
    except (HakoniwaComposerError, RecipeError, OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
