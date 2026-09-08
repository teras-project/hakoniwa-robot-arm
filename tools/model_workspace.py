#!/usr/bin/env python3
"""Resolve work-owned Model Forge directories."""

from __future__ import annotations

import argparse
import sys

from _hakoniwa_composer import (
    HakoniwaComposerError,
    model_forge_root,
    model_install_staging_dir,
    publish_model_install,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("robot_id")
    parser.add_argument(
        "directory",
        nargs="?",
        choices=("root", "source", "build", "install", "staging", "publish"),
        default="root",
    )
    args = parser.parse_args(argv)
    try:
        root = model_forge_root(args.robot_id)
        if args.directory == "publish":
            selected = publish_model_install(args.robot_id)
        elif args.directory == "staging":
            selected = model_install_staging_dir(args.robot_id)
        else:
            selected = root if args.directory == "root" else root / args.directory
        print(selected)
        return 0
    except HakoniwaComposerError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
