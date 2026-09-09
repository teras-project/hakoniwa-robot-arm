#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS_DIR))

from _hakoniwa_composer import HakoniwaComposerError, arm_root, workspace_work_dir  # noqa: E402


DEFAULT_PORT = 54001
DEFAULT_ROBOT = "nova5"


class Ros2TcpError(RuntimeError):
    pass


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise Ros2TcpError(f"failed to read JSON {path}: {error}") from error


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def robot_paths(robot_id: str) -> tuple[Path, Path, Path]:
    recipe_dir = arm_root() / "recipes" / robot_id
    manifest_path = recipe_dir / "asset-manifest.json"
    if not manifest_path.is_file():
        raise Ros2TcpError(f"robot manifest not found: {manifest_path}")
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise Ros2TcpError(f"manifest root must be an object: {manifest_path}")
    pdu_def_value = manifest.get("pdu_def")
    if not isinstance(pdu_def_value, str):
        raise Ros2TcpError(f"manifest has no pdu_def: {manifest_path}")
    return recipe_dir, manifest_path, (recipe_dir / pdu_def_value).resolve()


def resolve_pdu_contract(robot_id: str) -> tuple[str, list[dict[str, object]], Path, list[Path]]:
    recipe_dir, manifest_path, pdu_def_path = robot_paths(robot_id)
    manifest = load_json(manifest_path)
    pdu_def = load_json(pdu_def_path)
    if not isinstance(manifest, dict) or not isinstance(pdu_def, dict):
        raise Ros2TcpError("manifest and PDU definition must be JSON objects")

    robots = pdu_def.get("robots")
    paths = pdu_def.get("paths")
    if not isinstance(robots, list) or len(robots) != 1 or not isinstance(robots[0], dict):
        raise Ros2TcpError("ROS 2 TCP recipe currently requires exactly one robot per PDU definition")
    robot_name = robots[0].get("name")
    if not isinstance(robot_name, str) or not robot_name:
        raise Ros2TcpError("PDU definition robot name is missing")

    type_paths: list[Path] = []
    pdu_entries: list[dict[str, object]] = []
    if not isinstance(paths, list):
        raise Ros2TcpError("PDU definition paths must be an array")
    for entry in paths:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise Ros2TcpError("invalid PDU type path entry")
        type_path = (pdu_def_path.parent / str(entry["path"])).resolve()
        types = load_json(type_path)
        if not isinstance(types, list) or not all(isinstance(item, dict) for item in types):
            raise Ros2TcpError(f"PDU type file must contain an array: {type_path}")
        type_paths.append(type_path)
        pdu_entries.extend(types)

    components = manifest.get("components")
    if not isinstance(components, list):
        raise Ros2TcpError("manifest components must be an array")
    direction_by_name: dict[str, str] = {}
    for component in components:
        if not isinstance(component, dict):
            continue
        config_value = component.get("config")
        kind = component.get("kind")
        if not isinstance(config_value, str):
            continue
        component_config = load_json((recipe_dir / config_value).resolve())
        if not isinstance(component_config, dict):
            continue
        if kind == "controller" and component.get("type") == "joint_trajectory_controller":
            trajectory_input = component_config.get("input")
            if isinstance(trajectory_input, dict) and isinstance(trajectory_input.get("pdu_name"), str):
                direction_by_name[trajectory_input["pdu_name"]] = "ros_to_pdu"
        pdu_config = component_config.get("pdu_config")
        if not isinstance(pdu_config, dict) or not isinstance(pdu_config.get("pdu_name"), str):
            continue
        if kind == "actuator":
            direction_by_name[str(pdu_config["pdu_name"])] = "ros_to_pdu"
        elif kind == "state_output":
            direction_by_name[str(pdu_config["pdu_name"])] = "pdu_to_ros"

    selected: list[dict[str, object]] = []
    for pdu in pdu_entries:
        name = pdu.get("name")
        if isinstance(name, str) and name in direction_by_name:
            selected.append({**pdu, "direction": direction_by_name[name]})
    if not selected:
        raise Ros2TcpError("manifest exposes no actuator or state-output PDU bindings")
    return robot_name, selected, pdu_def_path, type_paths


def topic_for(pdu: dict[str, object]) -> str:
    pdu_type = pdu.get("type")
    direction = pdu.get("direction")
    if pdu_type == "trajectory_msgs/JointTrajectory" and direction == "ros_to_pdu":
        return "/joint_trajectory"
    if pdu_type == "sensor_msgs/JointState" and direction == "pdu_to_ros":
        return "/joint_states"
    return f"/{pdu['name']}"


def config_root(robot_id: str) -> Path:
    return (
        workspace_work_dir() / "recipes" / f"{robot_id}-joint-trajectory-control"
        / "config" / "ros2-tcp"
    )


def configure(robot_id: str, port: int, remote_host: str | None = None) -> Path:
    robot_name, pdus, pdu_def_path, type_paths = resolve_pdu_contract(robot_id)
    selected_remote_host = remote_host or os.environ.get(
        "HAKONIWA_ROS2_TCP_HOST", "host.docker.internal"
    )
    if not selected_remote_host.strip():
        raise Ros2TcpError("remote host must not be empty")
    output = config_root(robot_id)

    copied_def = load_json(pdu_def_path)
    write_json(output / "pdu" / "pdudef.json", copied_def)
    for type_path in type_paths:
        write_json(output / "pdu" / type_path.name, load_json(type_path))

    write_json(output / "cache" / "latest.json", {
        "type": "buffer",
        "name": f"{robot_id}_ros2_tcp_latest",
        "store": {"mode": "latest"},
    })
    write_json(output / "comm" / "shm.json", {
        "protocol": "shm",
        "impl_type": "callback",
        "name": f"{robot_id}_ros2_tcp_shm",
        "direction": "inout",
        "io": {"robots": [{
            "name": robot_name,
            "pdu": [{"name": pdu["name"], "notify_on_recv": False} for pdu in pdus],
        }]},
    })
    write_json(output / "comm" / "tcp-server.json", {
        "protocol": "tcp",
        "name": f"{robot_id}_ros2_tcp_server",
        "direction": "inout",
        "comm_raw_version": "v1",
        "role": "server",
        "local": {"address": "0.0.0.0", "port": port},
        "options": {"read_timeout_ms": 0, "write_timeout_ms": 0},
    })
    write_json(output / "comm" / "tcp-client.json", {
        "protocol": "tcp",
        "name": f"{robot_id}_ros2_tcp_client",
        "direction": "inout",
        "comm_raw_version": "v1",
        "role": "client",
        "remote": {"address": selected_remote_host, "port": port},
        "options": {"connect_timeout_ms": 5000, "read_timeout_ms": 0, "write_timeout_ms": 0},
    })

    endpoint_common = {"pdu_def_path": "../pdu/pdudef.json", "cache": "../cache/latest.json"}
    write_json(output / "endpoint" / "host-shm.json", {
        "name": f"{robot_id}_host_shm", **endpoint_common, "comm": "../comm/shm.json",
    })
    write_json(output / "endpoint" / "host-tcp.json", {
        "name": f"{robot_id}_host_tcp", **endpoint_common, "comm": "../comm/tcp-server.json",
    })
    write_json(output / "endpoint" / "docker-tcp.json", {
        "name": f"{robot_id}_docker_tcp", **endpoint_common, "comm": "../comm/tcp-client.json",
    })
    node_id = "arm_ros2_tcp_node"
    write_json(output / "endpoint" / "endpoint_container.json", [{
        "nodeId": node_id,
        "endpoints": [
            {"id": "host-shm", "mode": "local", "config_path": "host-shm.json", "direction": "inout"},
            {"id": "host-tcp", "mode": "local", "config_path": "host-tcp.json", "direction": "inout"},
        ],
    }])

    command_pdus = [pdu for pdu in pdus if pdu["direction"] == "ros_to_pdu"]
    state_pdus = [pdu for pdu in pdus if pdu["direction"] == "pdu_to_ros"]
    groups: dict[str, object] = {}
    connections: list[dict[str, object]] = []
    if command_pdus:
        groups["commands"] = [
            {"id": f"{robot_name}.{pdu['name']}", "robot_name": robot_name, "pdu_name": pdu["name"]}
            for pdu in command_pdus
        ]
        connections.append({
            "id": "tcp_to_shm", "nodeId": node_id,
            "source": {"endpointId": "host-tcp"},
            "destinations": [{"endpointId": "host-shm"}],
            "transferPdus": [{"pduKeyGroupId": "commands", "policyId": "immediate"}],
        })
    if state_pdus:
        groups["states"] = [
            {"id": f"{robot_name}.{pdu['name']}", "robot_name": robot_name, "pdu_name": pdu["name"]}
            for pdu in state_pdus
        ]
        connections.append({
            "id": "shm_to_tcp", "nodeId": node_id,
            "source": {"endpointId": "host-shm"},
            "destinations": [{"endpointId": "host-tcp"}],
            "transferPdus": [{"pduKeyGroupId": "states", "policyId": "ticker_20ms"}],
        })
    write_json(output / "bridge" / "bridge.json", {
        "version": "2.0.0",
        "transferPolicies": {
            "immediate": {"type": "immediate"},
            "ticker_20ms": {"type": "ticker", "intervalMs": 20},
        },
        "nodes": [{"id": node_id}],
        "endpoints_config_path": "../endpoint/endpoint_container.json",
        "wireLinks": [],
        "pduKeyGroups": groups,
        "connections": connections,
    })
    bindings = []
    for pdu in pdus:
        binding: dict[str, object] = {
            "pdu_key": {"robot_name": robot_name, "pdu_name": pdu["name"]},
            "direction": pdu["direction"],
            "topic": topic_for(pdu),
        }
        if pdu["direction"] == "pdu_to_ros":
            binding["qos"] = {
                "history": "keep_last", "depth": 10,
                "reliability": "best_effort", "durability": "volatile",
            }
        bindings.append(binding)
    write_json(output / "ros" / "binding.json", {
        "endpoint_config": "../endpoint/docker-tcp.json",
        "bindings": bindings,
    })
    write_json(output / "metadata.json", {
        "robot_id": robot_id,
        "robot_name": robot_name,
        "transport": "tcp",
        "host": {"role": "server", "port": port},
        "docker": {"role": "client", "host": selected_remote_host},
        "bindings": bindings,
    })
    print(output)
    return output


def foundation_prefix() -> Path:
    return workspace_work_dir() / "foundation" / "install"


def host_bridge_binary(robot_id: str) -> Path:
    configured = os.environ.get("HAKONIWA_PDU_BRIDGE_BIN")
    if configured:
        return Path(configured).expanduser().resolve()
    return foundation_prefix() / "bin" / "hakoniwa-pdu-web-bridge"


def doctor(robot_id: str) -> int:
    output = config_root(robot_id)
    checks = [
        ("generated binding", output / "ros" / "binding.json"),
        ("generated host bridge", output / "bridge" / "bridge.json"),
        ("generated endpoint container", output / "endpoint" / "endpoint_container.json"),
        ("host bridge binary", host_bridge_binary(robot_id)),
    ]
    failed = False
    for label, path in checks:
        ok = path.is_file()
        print(f"[{'OK' if ok else 'NG'}] {label}: {path}")
        failed = failed or not ok
    return 1 if failed else 0


def start_host(robot_id: str) -> int:
    output = config_root(robot_id)
    binary = host_bridge_binary(robot_id)
    if not binary.is_file():
        raise Ros2TcpError(f"host bridge binary not found: {binary}")
    command = [
        str(binary), "--config-root", str(output),
        "--node-name", "arm_ros2_tcp_node", "--asset-name", "Ros2TcpBridge",
        "--delta-time-step-usec", "20000",
    ]
    prefix = foundation_prefix()
    env = os.environ.copy()
    env.update({
        "HAKONIWA_HOME": str(prefix),
        "HAKONIWA_CORE_ROOT": str(prefix),
        "HAKONIWA_PDU_ENDPOINT_ROOT": str(prefix),
        "HAKO_CONFIG_PATH": str(workspace_work_dir() / "foundation" / "config" / "cpp_core_config.json"),
    })
    library_key = "PATH" if platform.system() == "Windows" else (
        "DYLD_LIBRARY_PATH" if platform.system() == "Darwin" else "LD_LIBRARY_PATH"
    )
    env[library_key] = os.pathsep.join([str(prefix / "lib"), env.get(library_key, "")])
    print("+", subprocess.list2cmdline(command), flush=True)
    return subprocess.run(command, cwd=arm_root(), env=env, check=False).returncode


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Configure the robot-independent ROS 2 TCP bridge")
    result.add_argument("command", choices=["configure", "config-root", "doctor", "start-host"])
    result.add_argument("--robot", default=DEFAULT_ROBOT)
    result.add_argument("--port", type=int, default=DEFAULT_PORT)
    result.add_argument(
        "--remote-host",
        default=None,
        help="TCP server hostname seen by the ROS side (default: HAKONIWA_ROS2_TCP_HOST or host.docker.internal)",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if not 1 <= args.port <= 65535:
            raise Ros2TcpError(f"port must be between 1 and 65535: {args.port}")
        if args.command == "configure":
            configure(args.robot, args.port, args.remote_host)
            return 0
        if args.command == "config-root":
            print(config_root(args.robot))
            return 0
        if args.command == "doctor":
            return doctor(args.robot)
        return start_host(args.robot)
    except (HakoniwaComposerError, Ros2TcpError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
