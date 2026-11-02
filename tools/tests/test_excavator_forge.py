from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from _hakoniwa_composer import venv_python  # noqa: E402


def load_forge():
    path = ROOT / "recipes/excavator/forge.py"
    spec = importlib.util.spec_from_file_location("excavator_forge_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_venv_python_uses_native_layout_without_resolving(tmp_path: Path):
    venv = tmp_path / "tools-venv"
    assert venv_python(venv, system="Linux") == venv / "bin/python"
    assert venv_python(venv, system="Darwin") == venv / "bin/python"
    assert venv_python(venv, system="Windows") == venv / "Scripts/python.exe"


def test_checksum_format_matches_shasum(tmp_path: Path):
    forge = load_forge()
    (tmp_path / "alpha.bin").write_bytes(b"alpha")
    output = forge.write_sha256sums(tmp_path, ("alpha.bin",))
    expected = hashlib.sha256(b"alpha").hexdigest()
    assert output.read_text(encoding="utf-8") == f"{expected}  alpha.bin\n"


def test_forge_declares_shell_step_outputs_and_checksum_order():
    forge = load_forge()
    assert forge.CHECKSUM_FILES == (
        "LICENSE",
        "excavator.runtime.xml",
        "excavator.mobile.xml",
        "excavator.bucket.xml",
        "excavator.bucket-proxy-debug.xml",
        "excavator.terrain.xml",
        "excavator.soil.xml",
        "excavator-worksite-height.png",
        "model/urdf/excavator.urdf",
    )
    source = (ROOT / "recipes/excavator/forge.py").read_text(encoding="utf-8")
    for label in (
        "Fetch Pinned Source", "Normalize URDF Meshes", "Convert URDF to MJCF",
        "Add Position Actuators", "Configure Stable Integration",
        "Exclude Adjacent Joint Contacts", "Add Six-wheel Differential Base",
        "Add Open Bucket Collision Shell", "Add HField Work Pit",
        "Add Simplified Granular Soil",
    ):
        assert label in source
