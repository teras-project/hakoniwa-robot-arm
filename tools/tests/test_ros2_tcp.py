from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


RECIPE_DIR = Path(__file__).resolve().parents[1] / "recipe"
sys.path.insert(0, str(RECIPE_DIR))

import ros2_tcp  # noqa: E402


class HostBridgeBinaryTest(unittest.TestCase):
    def test_windows_uses_exe_suffix(self) -> None:
        with (
            patch.dict(ros2_tcp.os.environ, {}, clear=True),
            patch.object(ros2_tcp.platform, "system", return_value="Windows"),
            patch.object(ros2_tcp, "foundation_prefix", return_value=Path("C:/foundation")),
        ):
            self.assertEqual(
                ros2_tcp.host_bridge_binary("nova5"),
                Path("C:/foundation/bin/hakoniwa-pdu-web-bridge.exe"),
            )

    def test_posix_keeps_extensionless_name(self) -> None:
        with (
            patch.dict(ros2_tcp.os.environ, {}, clear=True),
            patch.object(ros2_tcp.platform, "system", return_value="Linux"),
            patch.object(ros2_tcp, "foundation_prefix", return_value=Path("/foundation")),
        ):
            self.assertEqual(
                ros2_tcp.host_bridge_binary("nova5"),
                Path("/foundation/bin/hakoniwa-pdu-web-bridge"),
            )


if __name__ == "__main__":
    unittest.main()
