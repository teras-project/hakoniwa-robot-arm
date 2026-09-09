#!/usr/bin/env python3
"""Materialize the Core-free ROS topic-bridge recipe in a ROS-owned workspace."""
from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ARM_ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "hakoniwa-pdu-endpoint": "3e06ca5f4bd899d72639b4e0ac9452d88383c7ae",
    "hakoniwa-pdu-ros": "f180e38da1852d756b94a5a551a6e45812b5ce84",
}


def run(argv, **kwargs):
    print("+ " + shlex.join(map(str, argv)), file=sys.stderr, flush=True)
    return subprocess.run(list(map(str, argv)), check=True, **kwargs)


def resolve_workdir(value):
    selected = value or os.environ.get("HAKONIWA_ROS2_WS")
    if not selected:
        raise ValueError("set HAKONIWA_ROS2_WS or pass --workdir")
    root = Path(selected).expanduser().resolve()
    if root == ARM_ROOT or root in ARM_ROOT.parents:
        raise ValueError("ROS workdir must be a separate generated directory")
    return root


def source_path(value, name):
    return Path(value).expanduser().resolve() if value else ARM_ROOT.parent / name


def ensure_source(path, name):
    if not path.exists():
        run(["git", "clone", "--no-checkout", f"https://github.com/hakoniwalab/{name}.git", path])
        run(["git", "-C", path, "checkout", "--detach", SOURCES[name]])
    # Existing checkouts belong to the user; never checkout or pull them here.
    required = "CMakeLists.txt" if name.endswith("endpoint") else "package.xml"
    if not (path / required).is_file():
        raise ValueError(f"missing {required} in {path}")


def shell_environment(root, distro):
    q = shlex.quote
    return "\n".join([
        f"source {q('/opt/ros/' + distro + '/setup.bash')} || return $?",
        f"source {q(str(root / 'venv/bin/activate'))} || return $?",
        f"source {q(str(root / 'install/setup.bash'))} || return $?",
        "unset HAKONIWA_PDU_ENDPOINT_PYTHON_PATH HAKO_PDU_ENDPOINT_LIB_DIR PYTHONHOME",
        f"export HAKONIWA_ROS2_WS={q(str(root))}",
        'export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-73}"',
        f"export HAKO_PDU_ENDPOINT_SHARED_LIB={q(str(root / 'native/lib/libhakoniwa_pdu_endpoint.so'))}",
        f"export LD_LIBRARY_PATH={q(str(root / 'native/lib'))}" + '${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}',
        # ros2 is a system-Python entry point: expose the ROS venv packages to it.
        'export PYTHONPATH="$(' + q(str(root / 'venv/bin/python')) +
        " -c 'import site; print(site.getsitepackages()[0])')${PYTHONPATH:+:$PYTHONPATH}\"",
        "",
    ])


def check_platform(distro):
    if platform.system() != "Linux" or not Path(f"/opt/ros/{distro}/setup.bash").is_file():
        raise ValueError("run inside the matching Ubuntu/ROS environment")
    if os.environ.get("HAKONIWA_WORKSPACE_ACTIVE") == "1":
        raise ValueError("use a ROS terminal outside the Hakoniwa Foundation workspace")


def build(root, distro, endpoint, pdu_ros):
    check_platform(distro)
    identity = {"ros_distro": distro, "architecture": platform.machine(), "system_python": "/usr/bin/python3"}
    marker = root / "ros-workspace.json"
    if marker.is_file() and json.loads(marker.read_text())["identity"] != identity:
        raise ValueError("workspace belongs to another ROS/platform environment; select a fresh --workdir")
    if not marker.exists() and any((root / name).exists() for name in ("venv", "build", "install", "native")):
        raise ValueError("unmanaged build artifacts exist; select a fresh ROS workdir")
    ensure_source(endpoint, "hakoniwa-pdu-endpoint")
    ensure_source(pdu_ros, "hakoniwa-pdu-ros")
    root.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"identity": identity, "status": "building"}, indent=2) + "\n")
    env = os.environ.copy()
    for key in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "HAKO_PDU_ENDPOINT_LIB_DIR", "HAKONIWA_PDU_ENDPOINT_PYTHON_PATH"):
        env.pop(key, None)
    run(["/usr/bin/python3", "-m", "venv", "--system-site-packages", root / "venv"], env=env)
    python = root / "venv/bin/python"
    run([python, "-m", "pip", "install", "wheel", "setuptools>=68,<80", "cffi>=1.16", "hakoniwa-pdu==1.6.9"], env=env)
    run(["cmake", "-S", endpoint, "-B", root / "build/endpoint",
         "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_INSTALL_PREFIX={root / 'native'}",
         "-DCMAKE_INSTALL_LIBDIR=lib", "-DBUILD_SHARED_LIBS=ON", "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
         "-DHAKO_PDU_ENDPOINT_ENABLE_HAKONIWA_CORE=OFF",
         "-DHAKO_PDU_ENDPOINT_BUILD_TESTS=OFF", "-DHAKO_PDU_ENDPOINT_BUILD_EXAMPLES=OFF",
         "-DHAKO_PDU_ENDPOINT_BUILD_TOOLS=OFF", "-DHAKO_PDU_ENDPOINT_BUILD_BENCHMARKS=OFF"], env=env)
    run(["cmake", "--build", root / "build/endpoint", "--parallel", "2"], env=env)
    run(["cmake", "--install", root / "build/endpoint"], env=env)
    library = root / "native/lib/libhakoniwa_pdu_endpoint.so"
    if not library.is_file():
        raise ValueError(f"Endpoint installation did not produce {library}")
    env["HAKO_PDU_ENDPOINT_SHARED_LIB"] = str(library)
    env["HAKO_PDU_ENDPOINT_PYTHON_BUILD_DIR"] = str(root / "build/endpoint-python")
    ffi_script = endpoint / "python/hakoniwa_pdu_endpoint/build_c_endpoint_ffi.py"
    if "HAKO_PDU_ENDPOINT_PYTHON_BUILD_DIR" not in ffi_script.read_text():
        raise ValueError("Endpoint checkout lacks external Python build-dir support")
    run([python, ffi_script], env=env)
    site = Path(subprocess.check_output([str(python), "-c", "import site; print(site.getsitepackages()[0])"], text=True, env=env).strip())
    package = site / "hakoniwa_pdu_endpoint"
    shutil.copytree(endpoint / "python/hakoniwa_pdu_endpoint", package, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.so", "*.pyc"))
    extensions = list((root / "build/endpoint-python/hakoniwa_pdu_endpoint").glob("_c_endpoint_ffi*.so"))
    if not extensions:
        raise ValueError("Endpoint Python extension was not generated")
    for extension in extensions:
        shutil.copy2(extension, package / extension.name)
    env["PATH"] = str(python.parent) + os.pathsep + env.get("PATH", "")
    command = [str(python), "-m", "colcon", "--log-base", str(root / "log"), "build",
               "--base-paths", str(pdu_ros), str(ARM_ROOT / "ros2_packages/hakoniwa_arm_samples"),
               "--build-base", str(root / "build/ros"), "--install-base", str(root / "install"),
               "--symlink-install", "--packages-select", "hakoniwa_pdu_ros", "hakoniwa_arm_samples"]
    run(["bash", "-c", 'source "$1" && shift && exec "$@"', "ros-build",
         f"/opt/ros/{distro}/setup.bash", *command], cwd=root, env=env)
    (root / "activate.bash").write_text(shell_environment(root, distro))
    doctor(root)
    marker.write_text(json.dumps({"identity": identity, "status": "installed",
                                  "sources": {"endpoint": str(endpoint), "pdu_ros": str(pdu_ros)}}, indent=2) + "\n")
    print(f"ROS workspace installed: {root}")
    print(f"source {shlex.quote(str(root / 'activate.bash'))}")


def doctor(root):
    activation = root / "activate.bash"
    if not activation.is_file():
        raise ValueError("ROS workspace is not installed; run build first")
    for package, command in (("hakoniwa_pdu_ros", "bridge"),
                             ("hakoniwa_arm_samples", "control"),
                             ("hakoniwa_arm_samples", "monitor")):
        executable = root / "install" / package / "lib" / package / command
        if not executable.is_file():
            raise ValueError(f"missing installed ROS executable: {executable}")
    run(["bash", "-c", 'source "$1" && python -c "$2" && ros2 pkg executables hakoniwa_arm_samples',
         "ros-doctor", activation,
         "import rclpy, hakoniwa_pdu, hakoniwa_pdu_endpoint.c_endpoint, hakoniwa_pdu_ros; "
         "from hakoniwa_pdu_endpoint._c_endpoint_ffi import ffi, lib; "
         "from sensor_msgs.msg import JointState; from trajectory_msgs.msg import JointTrajectory"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "doctor", "env"])
    parser.add_argument("--workdir", help="default: HAKONIWA_ROS2_WS")
    parser.add_argument("--ros-distro", choices=["humble", "jazzy"], default=os.environ.get("ROS_DISTRO"))
    parser.add_argument("--endpoint-src", default=os.environ.get("HAKONIWA_PDU_ENDPOINT_SRC"))
    parser.add_argument("--pdu-ros-src", default=os.environ.get("HAKONIWA_PDU_ROS_SRC"))
    args = parser.parse_args()
    try:
        root = resolve_workdir(args.workdir)
        if args.command == "build":
            if args.ros_distro not in ("humble", "jazzy"):
                raise ValueError("set ROS_DISTRO or pass --ros-distro")
            build(root, args.ros_distro, source_path(args.endpoint_src, "hakoniwa-pdu-endpoint"),
                  source_path(args.pdu_ros_src, "hakoniwa-pdu-ros"))
        elif args.command == "doctor":
            doctor(root)
        else:
            if not (root / "activate.bash").is_file():
                raise ValueError("run build first")
            print(f"source {shlex.quote(str(root / 'activate.bash'))}")
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
