from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path


class HakoniwaComposerError(RuntimeError):
    pass


def arm_root() -> Path:
    return Path(__file__).resolve().parents[1]


def composer_root() -> Path:
    configured = (
        os.environ.get("HAKONIWA_COMPOSER", "").strip()
        or os.environ.get("HAKONIWA_BUSINESS_PACK_ROOT", "").strip()
    )
    root = Path(configured).expanduser() if configured else arm_root().parent / "hakoniwa-business-pack"
    root = root.resolve()
    if not (root / "tools" / "foundation.py").is_file():
        raise HakoniwaComposerError(
            "Hakoniwa Composer checkout was not found at "
            f"{root}; set HAKONIWA_COMPOSER to the repository root"
        )
    return root


def workspace_root() -> Path:
    root = composer_root()
    if os.environ.get("HAKONIWA_WORKSPACE_ACTIVE") != "1":
        return root

    configured = os.environ.get("HAKONIWA_WORKSPACE_ROOT", "").strip()
    if not configured:
        raise HakoniwaComposerError(
            "HAKONIWA_WORKSPACE_ACTIVE=1 requires HAKONIWA_WORKSPACE_ROOT"
        )
    active = Path(configured).expanduser().resolve()
    if active != root:
        raise HakoniwaComposerError(
            "active Hakoniwa workspace does not match Hakoniwa Composer: "
            f"active={active}, composer={root}"
        )
    return active


def workspace_work_dir() -> Path:
    """Return the active work directory using the Composer contract."""
    configured = os.environ.get("HAKONIWA_WORK_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    # An old activation has no HAKONIWA_WORK_DIR; retain its workspace-root
    # based default while keeping the inactive-process fallback local.
    active_root = os.environ.get("HAKONIWA_WORKSPACE_ROOT", "").strip()
    base = Path(active_root).expanduser() if active_root else composer_root()
    return (base / "work").resolve()


def model_forge_root(robot_id: str) -> Path:
    """Return the work-owned Forge root for a robot identifier."""
    if not robot_id or not all(character.isalnum() or character in "-_" for character in robot_id):
        raise HakoniwaComposerError(f"invalid robot identifier: {robot_id!r}")
    return workspace_work_dir() / "model-forge" / robot_id


def model_install_dir(robot_id: str) -> Path:
    """Return the work-owned directory containing runtime model artifacts."""
    return model_forge_root(robot_id) / "install"


def model_install_staging_dir(robot_id: str) -> Path:
    """Return the work-owned staging directory used before publishing."""
    return model_forge_root(robot_id) / ".install-next"


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def publish_model_install(robot_id: str) -> Path:
    """Replace install only after a complete staged tree is available.

    A prior install is restored if the second rename fails. A leftover backup
    from an interrupted publication is recovered before starting a new one.
    """
    root = model_forge_root(robot_id)
    install = root / "install"
    staging = model_install_staging_dir(robot_id)
    backup = root / ".install-previous"
    if not staging.is_dir() or staging.is_symlink():
        raise HakoniwaComposerError(
            f"staged Model Forge install is not a directory: {staging}"
        )

    if backup.exists() or backup.is_symlink():
        if not install.exists() and not install.is_symlink():
            backup.rename(install)
        else:
            _remove_path(backup)

    had_install = install.exists() or install.is_symlink()
    if had_install:
        install.rename(backup)
    try:
        staging.rename(install)
    except OSError:
        if had_install and not install.exists() and backup.exists():
            backup.rename(install)
        raise
    if backup.exists() or backup.is_symlink():
        _remove_path(backup)
    return install


class _FoundationAdapter:
    """Keep arm Recipe call sites on the Composer-owned workspace."""

    def __init__(self, module, root: Path):
        self._module = module
        self._root = root

    def resolve_workspace(
        self,
        _legacy_root: Path,
        recipe_id: str,
        foundation_root_override: Path | None = None,
    ):
        return self._module.resolve_workspace(
            self._root,
            recipe_id,
            foundation_root_override,
        )

    def __getattr__(self, name: str):
        return getattr(self._module, name)


def load_foundation_module():
    root = workspace_root()
    script = composer_root() / "tools" / "foundation.py"
    spec = importlib.util.spec_from_file_location("robot_arm_hakoniwa_composer_foundation", script)
    if spec is None or spec.loader is None:
        raise HakoniwaComposerError(f"cannot load Foundation implementation: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return _FoundationAdapter(module, root)


def load_foundation_consumer_module():
    script = (
        composer_root()
        / "foundation"
        / "python"
        / "hakoniwa_foundation_consumer.py"
    )
    if not script.is_file():
        raise HakoniwaComposerError(
            f"Foundation consumer API was not found: {script}"
        )
    spec = importlib.util.spec_from_file_location(
        "robot_arm_hakoniwa_foundation_consumer", script
    )
    if spec is None or spec.loader is None:
        raise HakoniwaComposerError(f"cannot load Foundation consumer API: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_workspace_module():
    root = composer_root()
    script = root / "tools" / "workspace.py"
    spec = importlib.util.spec_from_file_location("robot_arm_hakoniwa_composer_workspace", script)
    if spec is None or spec.loader is None:
        raise HakoniwaComposerError(f"cannot load Workspace implementation: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
