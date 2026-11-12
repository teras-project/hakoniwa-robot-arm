#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOLS_DIR))

from _hakoniwa_composer import (  # noqa: E402
    HakoniwaComposerError,
    arm_root,
    excavator_bucket_proxy_python,
    load_foundation_consumer_module,
    load_foundation_module,
    model_forge_root,
    model_install_dir,
    workspace_work_dir,
)


RECIPE_ID = ""
ROBOT_ID = ""
ROBOT_LABEL = ""
BUILD_CONFIGURATION = "Release"


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
            "Foundation is not reusable; resolve the reported Foundation "
            "diagnostic and rerun this command"
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
    return (
        "robot-excavator-hakoniwa-asset"
        if ROBOT_ID == "excavator"
        else "robot-arm-hakoniwa-asset"
    )


def binary(workspace) -> Path:
    suffix = ".exe" if platform.system() == "Windows" else ""
    return workspace.recipe_root / "build" / "bin" / f"{runtime_target()}{suffix}"


def hako_cmd_binary(prefix: Path) -> Path:
    suffix = ".exe" if platform.system() == "Windows" else ""
    return prefix / "bin" / f"hako-cmd{suffix}"


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
    if ROBOT_ID == "excavator":
        return "Robot excavator Hakoniwa asset started" in log
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


def update_excavator_checksums(robot_dir: Path, names: tuple[str, ...]) -> None:
    checksum_path = required(robot_dir / "SHA256SUMS", "excavator checksums")
    replacements = {
        name: hashlib.sha256((robot_dir / name).read_bytes()).hexdigest()
        for name in names
    }
    output = []
    seen = set()
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) == 2 and fields[1] in replacements:
            name = fields[1]
            output.append(f"{replacements[name]}  {name}")
            seen.add(name)
        else:
            output.append(line)
    missing = set(replacements) - seen
    if missing:
        raise RecipeError(f"SHA256SUMS is missing generated entries: {sorted(missing)}")
    checksum_path.write_text("\n".join(output) + "\n", encoding="utf-8")


def materialize_excavator_worksite() -> None:
    pack = arm_root()
    recipe = pack / "recipes/excavator"
    robot_dir = model_install_dir("excavator")
    tools_python = required(
        excavator_bucket_proxy_python(),
        "Recipe-owned bucket proxy Python; run python tools/install_excavator_bucket_proxy_tools.py",
    )
    steps = (
        [
            str(tools_python),
            str(pack / "tools/generate_excavator_bucket_collision.py"),
            str(robot_dir / "excavator.mobile.xml"),
            "--config", str(recipe / "bucket-collision.yaml"),
            "--output", str(robot_dir / "excavator.bucket.xml"),
            "--debug-output", str(robot_dir / "excavator.bucket-proxy-debug.xml"),
        ],
        [
            sys.executable,
            str(pack / "tools/generate_excavator_hfield.py"),
            str(robot_dir / "excavator.bucket.xml"),
            "--config", str(recipe / "config/environment/terrain.json"),
            "--heightmap-output", str(robot_dir / "excavator-worksite-height.png"),
            "--output", str(robot_dir / "excavator.terrain.xml"),
        ],
        [
            sys.executable,
            str(pack / "tools/generate_excavator_soil.py"),
            str(robot_dir / "excavator.terrain.xml"),
            "--config", str(recipe / "config/environment/soil.json"),
            "--output", str(robot_dir / "excavator.soil.xml"),
        ],
    )
    print("Materializing the excavator digging worksite from Recipe configuration.")
    for command in steps:
        if run(command, cwd=pack) != 0:
            raise RecipeError("excavator digging-worksite materialization failed")
    update_excavator_checksums(
        robot_dir,
        (
            "excavator.bucket.xml",
            "excavator.bucket-proxy-debug.xml",
            "excavator.terrain.xml",
            "excavator.soil.xml",
            "excavator-worksite-height.png",
        ),
    )
    print("Excavator digging worksite is up to date.")


def manifest_model_path(manifest: dict) -> Path:
    model = manifest.get("model")
    if not isinstance(model, str) or not model:
        raise RecipeError(f"{ROBOT_LABEL} manifest has no model")
    return model_install_dir(ROBOT_ID) / Path(model).name


def materialize_runtime_manifest(
    template: Path, workspace, sensor_implementation: str = "reference",
) -> Path:
    """Write a workspace-owned manifest with absolute runtime inputs.

    With a sensor implementation other than reference, the "sensors" component
    uses the robot's sensor set for it (so101-sensors.json -> so101-sensors-<name>.json)."""
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
        if (isinstance(value, str) and component.get("id") == "sensors"
                and sensor_implementation != "reference"):
            value = str(Path(value).with_name(f"{Path(value).stem}-{sensor_implementation}.json"))
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


def _write_profile(path: Path, lines: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _shell_export(name: str, value: Path | str) -> str:
    return f"export {name}={shlex.quote(str(value))}"


def _role_prompt(role: str) -> list[str]:
    quoted_role = shlex.quote(role)
    return [
        f"export HAKO_TERMINAL_ROLE={quoted_role}",
        'if [[ -n "${ZSH_VERSION:-}" ]]; then',
        f'  [[ "${{PROMPT:-}}" == *"({role})"* ]] || PROMPT="({role}) ${{PROMPT:-%n@%m %1~ %# }}"',
        "  PS1=\"${PROMPT}\"",
        'elif [[ -n "${BASH_VERSION:-}" ]]; then',
        f'  [[ "${{PS1:-}}" == *"({role})"* ]] || PS1="({role}) ${{PS1:-\\u@\\h \\W \\$ }}"',
        "fi",
    ]


def materialize_role_profiles(*, ros2_tcp: bool) -> list[Path]:
    """Generate local, configuration-owned shell entrypoints for an Arm Recipe.

    The common tool profile owns checkout discovery; these profiles own only
    the selected work paths and terminal role.  They intentionally live below
    HAKONIWA_WORK_DIR and are never part of the repository source tree.
    """
    work_dir = workspace_work_dir()
    profiles_dir = work_dir / "profiles"
    configured_ros2_work_dir = os.environ.get("HAKONIWA_ROS2_WS", "").strip()
    ros2_work_dir = (
        Path(configured_ros2_work_dir).expanduser()
        if configured_ros2_work_dir
        else work_dir / "ros2"
    )
    ros2_work_dir = ros2_work_dir.resolve()
    common_profile = arm_root() / "profiles/tool-env/activate.bash"
    common_source = f"source {shlex.quote(str(common_profile))} || return $?"
    common_lines = [
        "#!/usr/bin/env bash",
        "# Generated by hakoniwa-robot-arm configure. Do not edit.",
        common_source,
        _shell_export("HAKONIWA_WORK_DIR", work_dir),
        _shell_export("HAKONIWA_ROS2_WS", ros2_work_dir),
    ]
    generated = []
    hako_path = profiles_dir / "activate-host-hako.bash"
    generated.append(_write_profile(hako_path, [
        *common_lines,
        "export HAKO_TERMINAL_ROLE=host-hako",
        'if [[ "${HAKONIWA_WORKSPACE_ACTIVE:-}" == "1" ]]; then',
        '  echo "host-hako is already active; use this profile from a normal Host shell." >&2',
        "  return 1",
        "fi",
        'python3.12 "$HAKONIWA_COMPOSER/tools/workspace.py" enter --workdir "$HAKONIWA_WORK_DIR"',
    ]))
    if not ros2_tcp:
        return generated

    ros_build_path = profiles_dir / "activate-host-ros-build.bash"
    generated.append(_write_profile(ros_build_path, [
        *common_lines,
        *_role_prompt("host-ros-build"),
        "# This profile prepares the ROS work path. ros2_workspace.py build",
        "# selects and sources the requested ROS distribution itself.",
    ]))
    binding = (
        work_dir
        / "recipes"
        / f"{ROBOT_ID}-joint-trajectory-control"
        / "config/ros2-tcp/ros/binding.json"
    )
    for role in ("host-ros-bridge", "host-ros-monitor", "host-ros-control"):
        path = profiles_dir / f"activate-{role}.bash"
        generated.append(_write_profile(path, [
            *common_lines,
            _shell_export("HAKONIWA_ROS_BINDING", binding),
            'if [[ ! -f "$HAKONIWA_ROS2_WS/activate.bash" ]]; then',
            '  echo "ROS 2 workspace is not built: $HAKONIWA_ROS2_WS; run ros2_workspace.py build first." >&2',
            "  return 1",
            "fi",
            'source "$HAKONIWA_ROS2_WS/activate.bash" || return $?',
            *_role_prompt(role),
        ]))
    return generated


def configure(
    headless: bool,
    ros2_tcp: bool = False,
    manual_demo: bool = False,
    gamepad_controller: bool = False,
    digging_worksite: bool = False,
    arm_environment: bool = False,
    realtime_sync_cycle_msec: int = 0,
    joint_trajectory: bool = True,
    sensors: bool = False,
    viewer_state: bool = False,
    bridge_step_usec: int | None = None,
    sensor_implementation: str = "reference",
) -> int:
    if sensor_implementation != "reference" and not sensors:
        raise RecipeError("--sensor-implementation needs --sensors")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", sensor_implementation):
        raise RecipeError(f"--sensor-implementation is not an implementation name: {sensor_implementation}")
    if not ros2_tcp and (not joint_trajectory or bridge_step_usec is not None):
        raise RecipeError("--no-joint-trajectory and --bridge-step-usec need --ros2-tcp")
    if bridge_step_usec is not None and bridge_step_usec <= 0:
        raise RecipeError("--bridge-step-usec must be positive")
    if sum(bool(value) for value in (ros2_tcp, manual_demo, gamepad_controller)) > 1:
        raise RecipeError("--ros2-tcp, --manual-demo, and --gamepad are exclusive")
    if realtime_sync_cycle_msec < 0:
        raise RecipeError("--realtime-sync-cycle-msec must be >= 0")
    if viewer_state and not sensors:
        raise RecipeError("--viewer-state needs --sensors")
    foundation, workspace = workspace_and_foundation()
    foundation.prepare_workspace(workspace)
    python = foundation_python(foundation, workspace)
    if digging_worksite and ROBOT_ID != "excavator":
        raise RecipeError("--digging-worksite is available only for excavator")
    if digging_worksite and arm_environment:
        raise RecipeError("--digging-worksite and --environment are exclusive")
    effective_digging_worksite = digging_worksite or (
        arm_environment and ROBOT_ID == "excavator"
    )
    if effective_digging_worksite:
        materialize_excavator_worksite()
    if sensors:
        # The sensor manifest is the arm environment plus the sensors (the build
        # needs --sensors as well).
        if ROBOT_ID == "excavator" or effective_digging_worksite:
            raise RecipeError("--sensors is available only for the arm environment")
        arm_environment = True
    if arm_environment and ROBOT_ID != "excavator":
        materialize_arm_environment()
    manifest_name = "asset-manifest.json"
    if effective_digging_worksite:
        manifest_name = "asset-manifest-digging.json"
    elif sensors and viewer_state:
        # The sensors manifest and the states a Hakoniwa viewer reads.
        manifest_name = "asset-manifest-sensors-viewer.json"
    elif sensors:
        manifest_name = "asset-manifest-sensors.json"
    elif arm_environment:
        manifest_name = "asset-manifest-environment.json"
    manifest_template = required(
        arm_root() / "recipes" / ROBOT_ID / manifest_name,
        f"{ROBOT_LABEL} manifest",
    )
    manifest = materialize_runtime_manifest(manifest_template, workspace, sensor_implementation)
    sender = required(
        arm_root() / "tools/control/send_joint_trajectory.py",
        "trajectory sender",
    )
    trajectory = required(
        arm_root() / "recipes" / ROBOT_ID / "demo-trajectory.json",
        f"{ROBOT_LABEL} demo trajectory",
    )
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    component_ids = {
        component.get("id") for component in manifest_data.get("components", [])
    }
    mobile_base_enabled = "mobile_base" in component_ids
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

        config_root = ros2_tcp_recipe.configure(
            ROBOT_ID, ros2_tcp_recipe.DEFAULT_PORT, joint_trajectory=joint_trajectory,
            manifest_name=manifest_name)
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
                "--delta-time-step-usec", str(
                    bridge_step_usec if bridge_step_usec is not None
                    else ros2_tcp_recipe.DEFAULT_BRIDGE_DELTA_USEC),
            ],
            "depends_on": [f"{ROBOT_ID}-plant"],
            "delay_sec": 1,
        })
    else:
        if gamepad_controller:
            if mobile_base_enabled:
                gamepad_sender = required(
                    arm_root() / "tools/control/ps5_excavator_manual.py",
                    "excavator gamepad Manual Controller",
                )
                gamepad_args = [
                    str(gamepad_sender),
                    str(manifest),
                    "--mapping",
                    str(required(
                        arm_root() / "recipes" / ROBOT_ID / "ps5-controller-macos.json",
                        "excavator gamepad mapping",
                    )),
                ]
                gamepad_asset_name = f"{ROBOT_ID}-ps5-controller"
            else:
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
        elif mobile_base_enabled and manual_demo:
            manual_sender = required(
                arm_root() / "recipes/excavator/demos/send_excavator_manual_demo.py",
                "excavator manual demo sender",
            )
            manual_sequence = required(
                arm_root() / "recipes" / ROBOT_ID / "demo-manual.json",
                f"{ROBOT_LABEL} manual sequence",
            )
            assets.append({
                "name": f"{ROBOT_ID}-manual-demo-sender",
                "activation_timing": "after_start",
                "command": str(python),
                "args": [
                    str(manual_sender), str(manifest),
                    "--sequence", str(manual_sequence), "--keep-alive",
                ],
                "depends_on": [f"{ROBOT_ID}-plant"],
                "delay_sec": 1,
            })
        elif mobile_base_enabled:
            excavator_demo = required(
                arm_root() / "recipes/excavator/demos/send_excavator_demo.py",
                "excavator demo sender",
            )
            drive_sequence = required(
                arm_root() / "recipes" / ROBOT_ID / "demo-drive.json",
                f"{ROBOT_LABEL} drive sequence",
            )
            assets.append({
                "name": f"{ROBOT_ID}-demo-sender",
                "activation_timing": "after_start",
                "command": str(python),
                "args": [
                    str(excavator_demo), str(manifest),
                    "--drive", str(drive_sequence),
                    "--trajectory", str(trajectory),
                ],
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
    profiles = materialize_role_profiles(ros2_tcp=ros2_tcp)
    print(f"Recipe workspace: {workspace.recipe_root}")
    print(f"Launcher        : {output}")
    print("Profiles        : " + ", ".join(str(path) for path in profiles))
    print(f"Mode            : {'headless' if headless else 'viewer'}")
    print(f"ROS 2 TCP       : {('enabled (no joint trajectory input)' if not joint_trajectory else 'enabled') if ros2_tcp else 'disabled'}")
    print(f"Manual demo     : {'enabled' if manual_demo else 'disabled'}")
    print(f"Gamepad         : {'enabled' if gamepad_controller else 'disabled'}")
    print(f"Digging worksite: {'enabled' if effective_digging_worksite else 'disabled'}")
    print(f"Arm environment : {'enabled' if arm_environment else 'disabled'}")
    print(f"Sensors         : {f'enabled ({sensor_implementation})' if sensors else 'disabled'}")
    print(
        "Realtime pacing : "
        + (
            f"{realtime_sync_cycle_msec} ms simulation-time cycle"
            if realtime_sync_cycle_msec > 0
            else "disabled"
        )
    )
    return 0


def bucket_proxy(viewer: bool) -> int:
    if ROBOT_ID != "excavator":
        raise RecipeError("bucket-proxy is available only for excavator")
    pack = arm_root()
    tools_python = excavator_bucket_proxy_python()
    if not tools_python.is_file():
        raise RecipeError(
            "Recipe-owned bucket proxy Python is missing; run: "
            "python tools/install_excavator_bucket_proxy_tools.py"
        )
    generator = required(
        pack / "tools/generate_excavator_bucket_collision.py",
        "bucket collision generator",
    )
    analyzer = required(
        pack / "tools/analyze_excavator_bucket_collision.py",
        "bucket collision analyzer",
    )
    config = required(
        pack / "recipes/excavator/bucket-collision.yaml",
        "bucket collision calibration YAML",
    )
    mobile = required(
        model_install_dir("excavator") / "excavator.mobile.xml",
        "excavator mobile model",
    )
    bucket = model_install_dir("excavator") / "excavator.bucket.xml"
    debug_model = model_install_dir("excavator") / "excavator.bucket-proxy-debug.xml"
    analysis_dir = workspace_work_dir() / "tools/excavator-bucket-proxy"
    analysis_svg = analysis_dir / "bucket-proxy-sections.svg"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    if run(
        [
            str(tools_python), str(analyzer),
            "--mesh", str(model_install_dir("excavator") / "model/meshes/stick_bucket_link.STL"),
            "--config", str(config),
            "--output", str(analysis_svg),
        ],
        cwd=pack,
    ) != 0:
        return 1
    command = [
        str(tools_python), str(generator), str(mobile),
        "--config", str(config),
        "--output", str(bucket),
        "--debug-output", str(debug_model),
        *(["--viewer"] if viewer else []),
    ]
    if run(command, cwd=pack) != 0:
        return 1
    print(f"Calibration YAML: {config}")
    print(f"Debug model     : {debug_model}")
    print(f"Reference SVG   : {analysis_svg}")
    status_match = re.search(
        r"(?m)^\s*status:\s*([A-Za-z0-9_-]+)\s*$",
        config.read_text(encoding="utf-8"),
    )
    print(f"Calibration     : {status_match.group(1) if status_match else 'unknown'}")
    return 0


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> int:
    print("+", subprocess.list2cmdline(command), flush=True)
    return subprocess.run(command, cwd=cwd, env=env, check=False).returncode


def sensor_cmake_args() -> list[str]:
    """The sensor stage and the linked sensor implementations, from the environment:
    HAKO_ROBOT_ARM_SENSOR_IMPLEMENTATIONS (default reference: hakoniwa-sensor-adapter's
    implementation that returns the true values, built from source) and
    HAKO_ROBOT_ARM_SENSOR_LIBRARIES (the libraries of the other implementations)."""
    implementations = os.environ.get("HAKO_ROBOT_ARM_SENSOR_IMPLEMENTATIONS", "reference").strip()
    libraries = os.environ.get("HAKO_ROBOT_ARM_SENSOR_LIBRARIES", "").strip()
    names = [name.strip() for name in implementations.split(";") if name.strip()]
    if not names:
        raise RecipeError("HAKO_ROBOT_ARM_SENSOR_IMPLEMENTATIONS lists no sensor implementation")
    if any(name != "reference" for name in names) and not libraries:
        raise RecipeError(
            "HAKO_ROBOT_ARM_SENSOR_IMPLEMENTATIONS lists an implementation other than reference: "
            "set HAKO_ROBOT_ARM_SENSOR_LIBRARIES to its libraries "
            "(the hakoniwa implementation is provided by Hakoniwa Lab)")
    return [
        "-DHAKO_ROBOT_ARM_ENABLE_SENSOR=ON",
        f"-DHAKO_ROBOT_ARM_SENSOR_IMPLEMENTATIONS={implementations}",
        f"-DHAKO_ROBOT_ARM_SENSOR_LIBRARIES={libraries}",
    ]


def build(
    mujoco_root: Path,
    headless: bool,
    sensors: bool = False,
    controller_plugin: bool = False,
) -> int:
    foundation, workspace = workspace_and_foundation()
    foundation_consumer = load_foundation_consumer_module()
    required(mujoco_root / "src/CMakeLists.txt", "hakoniwa-mujoco-robots sibling")
    build_dir = workspace.recipe_root / "build"
    configure_command = [
        "cmake", "-S", str(arm_root()), "-B", str(build_dir),
        f"-DCMAKE_BUILD_TYPE={BUILD_CONFIGURATION}",
        *foundation_consumer.cmake_consumer_args(workspace),
        f"-DHAKONIWA_FOUNDATION_PREFIX={workspace.install_prefix}",
        f"-DHAKONIWA_MUJOCO_ROBOTS_ROOT={mujoco_root}",
        "-DHAKO_USE_THIRDPARTY_HAKONIWA=OFF",
        f"-DHAKO_ARM_ENABLE_VIEWER={'OFF' if headless else 'ON'}",
        *(sensor_cmake_args() if sensors else []),
        f"-DHAKO_ROBOT_ARM_CONTROLLER_PLUGIN={'ON' if controller_plugin else 'OFF'}",
        "-DHAKO_ARM_ENABLE_DOBOT=OFF",
    ]
    if platform.system() == "Windows":
        # FetchContent's MSBuild sub-builds nest about 140 characters below
        # their base directory; keep that base short so Recipe build paths
        # stay under the 260-character MAX_PATH.
        configure_command.append(
            f"-DFETCHCONTENT_BASE_DIR={workspace.work_root / 'fc' / ROBOT_ID}"
        )
    env = environment(foundation, workspace)
    if run(configure_command, cwd=arm_root(), env=env) != 0:
        return 1
    return run(
        [
            "cmake", "--build", str(build_dir),
            "--config", BUILD_CONFIGURATION,
            "--target", runtime_target(), "--parallel", "2",
        ],
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
    hako_cmd = hako_cmd_binary(workspace.install_prefix)
    checks = (
        ("Hakoniwa Composer Foundation engine", True, "reused from configured checkout"),
        ("hakoniwa-mujoco-robots sibling", (mujoco_root / "src/CMakeLists.txt").is_file(), str(mujoco_root)),
        ("Foundation Python", python.is_file(), str(python)),
        ("hako-cmd", hako_cmd.is_file(), str(hako_cmd)),
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


def observed_nonzero_wheel_control(log_content: str) -> bool:
    for payload in re.findall(r"ctrl=\[([^\]]+)\]", log_content):
        try:
            controls = [float(value.strip()) for value in payload.split(",")]
        except ValueError:
            continue
        if len(controls) >= 6 and any(abs(value) > 0.05 for value in controls[-6:]):
            return True
    return False


def excavator_ground_motion_is_stable(log_content: str) -> bool:
    samples = []
    pattern = re.compile(
        r"time=\s*([0-9.]+).*?base_xy=\[\s*([-0-9.]+),\s*([-0-9.]+)\]"
        r".*?base_z=([-0-9.]+).*?up_z=([-0-9.]+)"
    )
    for match in pattern.finditer(log_content):
        time_sec, x_m, y_m, z_m, up_z = map(float, match.groups())
        if time_sec >= 1.0:
            samples.append((x_m, y_m, z_m, up_z))
    if len(samples) < 2:
        return False
    displacement_m = (
        (samples[-1][0] - samples[0][0]) ** 2
        + (samples[-1][1] - samples[0][1]) ** 2
    ) ** 0.5
    heights = [sample[2] for sample in samples]
    return (
        displacement_m >= 0.5
        and max(heights) - min(heights) <= 0.08
        and min(sample[3] for sample in samples) >= 0.98
    )


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
    demo_log = workspace.recipe_logs / f"{ROBOT_ID}-demo-sender.out"
    bridge_log = workspace.recipe_logs / f"{ROBOT_ID}-ros2-tcp-bridge.out"
    launcher = json.loads((workspace.recipe_config / "launcher.json").read_text(encoding="utf-8"))
    asset_names = {asset.get("name") for asset in launcher.get("assets", [])}
    ros2_tcp = f"{ROBOT_ID}-ros2-tcp-bridge" in asset_names
    excavator_demo_enabled = f"{ROBOT_ID}-demo-sender" in asset_names
    manual_demo_enabled = f"{ROBOT_ID}-manual-demo-sender" in asset_names
    gamepad_asset_name = next(
        (
            name for name in (
                f"{ROBOT_ID}-gamepad-controller",
                f"{ROBOT_ID}-ps5-controller",
            )
            if name in asset_names
        ),
        None,
    )
    gamepad_controller_enabled = gamepad_asset_name is not None
    current = None
    for _ in range(40):
        current = state(status_command, env)
        plant = plant_log.read_text(encoding="utf-8", errors="replace") if plant_log.is_file() else ""
        sender = sender_log.read_text(encoding="utf-8", errors="replace") if sender_log.is_file() else ""
        demo = demo_log.read_text(encoding="utf-8", errors="replace") if demo_log.is_file() else ""
        bridge = bridge_log.read_text(encoding="utf-8", errors="replace") if bridge_log.is_file() else ""
        ready_peer = "initializing endpoint container" in bridge if ros2_tcp else "Successfully sent" in sender
        if excavator_demo_enabled:
            ready_peer = "Excavator demo phase 1/3" in demo
        if manual_demo_enabled:
            manual_log = workspace.recipe_logs / f"{ROBOT_ID}-manual-demo-sender.out"
            manual = manual_log.read_text(encoding="utf-8", errors="replace") if manual_log.is_file() else ""
            ready_peer = "Manual command[0]" in manual
        if gamepad_controller_enabled:
            gamepad_log = workspace.recipe_logs / f"{gamepad_asset_name}.out"
            gamepad = gamepad_log.read_text(encoding="utf-8", errors="replace") if gamepad_log.is_file() else ""
            ready_peer = "pygame controller:" in gamepad or "PS5 controller:" in gamepad
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
        plant_error_log = workspace.recipe_logs / f"{ROBOT_ID}-plant.err"
        demo_log = workspace.recipe_logs / f"{ROBOT_ID}-demo-sender.out"
        sender_log = workspace.recipe_logs / f"{ROBOT_ID}-trajectory-sender.out"
        launcher = json.loads(
            (workspace.recipe_config / "launcher.json").read_text(encoding="utf-8")
        )
        twist_enabled = any(
            asset.get("name") == f"{ROBOT_ID}-demo-sender"
            for asset in launcher.get("assets", [])
        )
        for _ in range(40):
            content = plant_log.read_text(encoding="utf-8", errors="replace") if plant_log.is_file() else ""
            sender = (
                sender_log.read_text(encoding="utf-8", errors="replace")
                if sender_log.is_file()
                else ""
            )
            command_observed = (
                "Accepted JointTrajectory" in content
                if ROBOT_ID == "excavator"
                else "Successfully sent" in sender
            )
            if command_observed:
                if twist_enabled:
                    for _ in range(50):
                        twist = (
                            demo_log.read_text(encoding="utf-8", errors="replace")
                            if demo_log.is_file()
                            else ""
                        )
                        if "Successfully completed Twist sequence" in twist:
                            break
                        time.sleep(0.5)
                    else:
                        print(
                            f"[NG] staged excavator drive did not complete: {demo_log}",
                            file=sys.stderr,
                        )
                        return 1
                else:
                    time.sleep(1.0)
                content = plant_log.read_text(encoding="utf-8", errors="replace")
                plant_error = (
                    plant_error_log.read_text(encoding="utf-8", errors="replace")
                    if plant_error_log.is_file()
                    else ""
                )
                combined_plant_log = f"{content}\n{plant_error}".lower()
                instability_markers = (
                    "simulation is unstable",
                    "nan, inf or huge value",
                )
                if any(marker in combined_plant_log for marker in instability_markers):
                    print(
                        "[NG] MuJoCo numerical instability was observed: "
                        f"{plant_log}, {plant_error_log}",
                        file=sys.stderr,
                    )
                    return 1
                if twist_enabled and not observed_nonzero_wheel_control(content):
                    print(
                        f"[NG] non-zero crawler wheel control was not observed: {plant_log}",
                        file=sys.stderr,
                    )
                    return 1
                if twist_enabled and not excavator_ground_motion_is_stable(content):
                    print(
                        f"[NG] crawler travel was not grounded and stable: {plant_log}",
                        file=sys.stderr,
                    )
                    return 1
                if ROBOT_ID == "excavator":
                    print(f"[OK] {ROBOT_LABEL} accepted the Launcher-managed command input.")
                else:
                    print(f"[OK] {ROBOT_LABEL} Launcher-managed JointTrajectory PDU send completed.")
                if twist_enabled:
                    print(f"[OK] {ROBOT_LABEL} completed the Launcher-managed Twist sequence.")
                    print(f"[OK] {ROBOT_LABEL} applied non-zero crawler wheel controls.")
                    print(f"[OK] {ROBOT_LABEL} moved without chassis jump or tip-over.")
                print(
                    f"[OK] No MuJoCo numerical-instability marker was observed for "
                    f"{ROBOT_LABEL} during the smoke window."
                )
                return 0
            time.sleep(0.5)
        evidence_log = plant_log if ROBOT_ID == "excavator" else sender_log
        print(f"[NG] command evidence was not observed: {evidence_log}", file=sys.stderr)
        return 1
    finally:
        run(launcher_command(foundation, workspace, "terminate"), env=environment(foundation, workspace))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=f"Configure and operate the {ROBOT_LABEL} arm Recipe")
    commands = ["configure", "build", "doctor", "start", "status", "stop", "smoke"]
    if ROBOT_ID == "excavator":
        commands.append("bucket-proxy")
    result.add_argument("command", choices=commands)
    result.add_argument("--headless", action="store_true")
    result.add_argument("--ros2-tcp", action="store_true", help="launch the host SHM/TCP bridge instead of the demo sender")
    result.add_argument(
        "--no-joint-trajectory", dest="joint_trajectory", action="store_false",
        help="with --ros2-tcp: do not bridge the Runtime's JointTrajectory input "
             "(the ROS side sends interpolated joint commands)")
    result.add_argument(
        "--bridge-step-usec", type=int, default=None,
        help="with --ros2-tcp: the host bridge step in usec (default 20000); the Robot Runtime "
             "physics step (2000) for commands at 50 Hz or faster")
    result.add_argument("--manual-demo", action="store_true", help="launch the excavator Manual Controller demo instead of Auto")
    result.add_argument(
        "--gamepad", dest="gamepad_controller", action="store_true",
        help="launch the pygame gamepad input adapter instead of the Auto demo")
    result.add_argument(
        "--ps5-controller", dest="gamepad_controller", action="store_true",
        help=argparse.SUPPRESS)
    result.add_argument("--digging-worksite", action="store_true", help="select the explicit HField, accepted bucket-proxy, and simplified-soil manifest")
    result.add_argument("--environment", action="store_true", help="select the robot-specific Recipe environment")
    result.add_argument(
        "--sensors", action="store_true",
        help="SO-101: the arm environment with the overhead 3D LiDAR and the wrist force-torque sensor "
             "(configure and build)")
    result.add_argument(
        "--sensor-implementation", default="reference",
        help="with --sensors: the sensor set of the robot to use, by implementation (default reference: "
             "the true values; hakoniwa: the robot's set for Hakoniwa's sensor models)")
    result.add_argument(
        "--controller-plugin", action="store_true",
        help="build the Runtime's controller plugin loader (manifest components of type "
             "\"plugin\"; build only)")
    result.add_argument(
        "--viewer-state", action="store_true",
        help="SO-101 with --sensors: also the states a Hakoniwa viewer reads "
             "(viewer_joint_states with joints named SO101/<joint>, viewer_body_states with the cube pose)")
    result.add_argument("--realtime-sync-cycle-msec", type=int, default=0, help="reconcile simulation and wall time at this simulation-time interval; 0 disables pacing")
    result.add_argument("--viewer", action="store_true", help="open the bucket proxy calibration Viewer")
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
                args.manual_demo,
                args.gamepad_controller,
                args.digging_worksite,
                args.environment,
                args.realtime_sync_cycle_msec,
                args.joint_trajectory,
                args.sensors,
                args.viewer_state,
                args.bridge_step_usec,
                args.sensor_implementation,
            )
        if args.command == "bucket-proxy":
            return bucket_proxy(args.viewer)
        if args.command == "build":
            return build(
                absolute(args.mujoco_root), args.headless, args.sensors, args.controller_plugin)
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
