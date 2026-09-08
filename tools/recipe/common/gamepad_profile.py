from __future__ import annotations

import platform
from pathlib import Path


class UnsupportedGamepadPlatform(ValueError):
    pass


def resolve_dualsense_profile(
    pack_root: Path,
    *,
    system_name: str | None = None,
    release: str | None = None,
) -> tuple[Path, str]:
    system_name = system_name or platform.system()
    release = release or platform.release()

    if system_name == "Darwin":
        return (
            pack_root / "profiles/gamepads/dualsense/macos-pygame.json",
            "DualSense macOS pygame profile",
        )

    if system_name == "Linux":
        release_lower = release.lower()
        if "microsoft" in release_lower or "wsl" in release_lower:
            raise UnsupportedGamepadPlatform(
                "gamepad control is not supported on WSL; use native Ubuntu or macOS"
            )
        return (
            pack_root / "profiles/gamepads/dualsense/ubuntu-pygame.json",
            "DualSense Ubuntu pygame profile",
        )

    raise UnsupportedGamepadPlatform(
        f"gamepad control is supported only on native Ubuntu and macOS; host={system_name}"
    )
