"""SO-101 in a Hakoniwa three.js viewer (hakoniwa-threejs-drone): the WebSocket
bridge configuration and the viewer configuration.

The Robot Runtime writes, with configure --sensors --viewer-state, the states a
viewer reads: viewer_joint_states (sensor_msgs/JointState, joints named
SO101/<joint>) and viewer_body_states (sensor_msgs/MultiDOFJointState, the
cube's pose). The Hakoniwa PDU web bridge (an asset, hakoniwa-pdu-web-bridge)
carries them from shared memory to WebSocket; the viewer draws the arm (its
joints) and the cube (its pose) from the view-models of so101_view_model.py.

Writes, under <output> (default: the work directory's model-forge/so101/viewer):

  web-bridge/   the bridge's config root (--config-root), its node arm_viewer_node
  browser/      pdudef.json, vehicle-types.json, scene-config.json, viewer-config.json

The browser loads files by their path under the served root (--http-root, the
directory with the sibling checkouts and the work directory). Prints the
viewer's URL.

python3 tools/recipe/so101_viewer_config.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hakoniwa_composer import workspace_work_dir  # noqa: E402

ARM_ROOT = Path(__file__).resolve().parents[2]
ROBOT = "SO101"
STATE_PDUS = ("viewer_joint_states", "viewer_body_states")
NODE = "arm_viewer_node"


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def served(path: Path, http_root: Path) -> str:
    try:
        return "/" + path.resolve().relative_to(http_root.resolve()).as_posix()
    except ValueError as error:
        raise SystemExit(f"{path} is not under the served root {http_root}") from error


def main() -> int:
    work = workspace_work_dir()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=work / "model-forge/so101/viewer")
    parser.add_argument("--http-root", type=Path, default=ARM_ROOT.parent)
    parser.add_argument("--http-port", type=int, default=8000)
    parser.add_argument("--ws-port", type=int, default=8765)
    args = parser.parse_args()
    out = args.output
    for name in ("so101", "grasp_cube", "environment"):
        if not (out / name).is_dir():
            raise SystemExit(f"no view-model in {out / name}: run tools/recipe/so101_view_model.py first")

    # The two PDUs, with the channel IDs of the Robot Runtime's PDU definition.
    types = json.loads((ARM_ROOT / "recipes/so101/config/pdu/so101-pdutypes.json").read_text(encoding="utf-8"))
    state_types = [entry for entry in types if entry["name"] in STATE_PDUS]
    if len(state_types) != len(STATE_PDUS):
        raise SystemExit("so101-pdutypes.json has no viewer_joint_states / viewer_body_states")

    bridge = out / "web-bridge"
    write_json(bridge / "pdu/so101-viewer-pdutypes.json", state_types)
    write_json(bridge / "pdu/so101-viewer-pdudef.json", {
        "paths": [{"id": "so101-viewer", "path": "so101-viewer-pdutypes.json"}],
        "robots": [{"name": ROBOT, "pdutypes_id": "so101-viewer"}],
    })
    write_json(bridge / "cache/latest.json", {"type": "buffer", "name": "so101_viewer_latest", "store": {"mode": "latest"}})
    write_json(bridge / "comm/shm.json", {
        "protocol": "shm", "impl_type": "callback", "name": "so101_viewer_shm", "direction": "inout",
        "io": {"robots": [{"name": ROBOT, "pdu": [{"name": name, "notify_on_recv": False} for name in STATE_PDUS]}]},
    })
    write_json(bridge / "comm/ws.json", {
        "protocol": "websocket", "name": "so101_viewer_ws", "direction": "inout", "role": "server",
        "comm_raw_version": "v2", "local": {"port": args.ws_port},
        "options": {"connect_timeout_ms": 5000, "read_timeout_ms": 5000, "write_timeout_ms": 5000,
                    "ping_interval_sec": 30, "handshake_timeout_ms": 5000},
    })
    for name, comm in (("shm", "shm.json"), ("ws", "ws.json")):
        write_json(bridge / f"endpoint/{name}.json", {
            "name": f"so101-viewer-{name}-ep", "pdu_def_path": "../pdu/so101-viewer-pdudef.json",
            "cache": "../cache/latest.json", "comm": f"../comm/{comm}",
        })
    write_json(bridge / "endpoint/endpoint_container.json", [{
        "nodeId": NODE,
        "endpoints": [
            {"id": "bridge-shm-ep", "mode": "local", "config_path": "shm.json", "direction": "in"},
            {"id": "bridge-ws-ep", "mode": "local", "config_path": "ws.json", "direction": "out"},
        ],
    }])
    write_json(bridge / "bridge/bridge.json", {
        "version": "2.0.0",
        "transferPolicies": {"ticker_20ms": {"type": "ticker", "intervalMs": 20}},
        "nodes": [{"id": NODE}],
        "endpoints_config_path": "../endpoint/endpoint_container.json",
        "wireLinks": [],
        "pduKeyGroups": {"so101_viewer_state": [
            {"id": f"{ROBOT}.{name}", "robot_name": ROBOT, "pdu_name": name} for name in STATE_PDUS]},
        "connections": [{
            "id": "conn_so101_viewer_shm_to_ws", "nodeId": NODE,
            "source": {"endpointId": "bridge-shm-ep"},
            "destinations": [{"endpointId": "bridge-ws-ep"}],
            "transferPdus": [{"pduKeyGroupId": "so101_viewer_state", "policyId": "ticker_20ms"}],
        }],
    })

    # The scenery (floor, sensor housing), where so101_view_model.py found it.
    scenery = json.loads((out / "environment/environment.json").read_text(encoding="utf-8"))
    environments = [
        {"name": body["name"], "model": served(out / "environment/parts" / f"{body['name']}.glb", args.http_root),
         "pos": body["pos"], "groundTexture": False}
        for body in scenery
    ]

    browser = out / "browser"
    write_json(browser / "vehicle-types.json", {
        "so101": {"viewModelPath": served(out / "so101/view-model.json", args.http_root)},
        "grasp_cube": {"viewModelPath": served(out / "grasp_cube/view-model.json", args.http_root)},
    })
    write_json(browser / "scene-config.json", {
        "version": "1.0",
        "format": "compact",
        "environments": environments,
        "main_camera": {"fov": 50, "near": 0.01, "far": 100, "initialMode": "fixed",
                        "position": [0.7, -0.6, 0.5], "target": ROBOT},
        "vehicleTypesPath": "./vehicle-types.json",
        # The vehicle named after the PDU robot takes the joints SO101/<joint>; the
        # cube takes its pose (the arm stays at the origin: it has no pose PDU).
        "vehicles": [{"name": ROBOT, "type": "so101"}, {"name": "grasp_cube", "type": "grasp_cube"}],
    })
    write_json(browser / "viewer-config.json", {
        "version": "1.0",
        "three": {"sceneConfigPath": served(browser / "scene-config.json", args.http_root),
                  "initialCameraMode": "free"},
        "pdu": {"pduDefPath": served(bridge / "pdu/so101-viewer-pdudef.json", args.http_root),
                "wsUri": f"ws://127.0.0.1:{args.ws_port}", "wireVersion": "v2"},
        "ui": {"enableAttachedCameras": False, "enableMainCameraMouseControl": True,
               "statePanelIntervalMsec": 20},
        "stateInput": {"mode": "none", "vehicles": {"roleMap": {
            "vehicle_states": "sensor_msgs/MultiDOFJointState",
            "joint_states": "sensor_msgs/JointState",
        }}},
    })
    threejs = args.http_root / "hakoniwa-threejs-drone/index.html"
    print(f"bridge config root: {bridge}")
    print(f"viewer: http://127.0.0.1:{args.http_port}{served(threejs, args.http_root)}"
          f"?viewerConfigPath={served(browser / 'viewer-config.json', args.http_root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
