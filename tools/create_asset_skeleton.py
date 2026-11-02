#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def load_manifest(manifest_file: Path) -> dict:
    try:
        with manifest_file.open("r", encoding="utf-8") as file_obj:
            data = json.load(file_obj)
    except json.JSONDecodeError as exc:
        fail(
            f"Failed to parse asset manifest "
            f"'{manifest_file}': {exc}"
        )
    except OSError as exc:
        fail(
            f"Failed to read asset manifest "
            f"'{manifest_file}': {exc}"
        )

    if not isinstance(data, dict):
        fail("Asset manifest root must be a JSON object.")

    return data


def collect_config_paths(manifest: dict) -> list[str]:
    paths: list[str] = []

    #
    # Top-level runtime configuration files.
    #
    for key in ("pdu_def", "endpoint"):
        value = manifest.get(key)

        if isinstance(value, str) and value.strip():
            paths.append(value.strip())

    #
    # Component configuration files.
    #
    components = manifest.get("components", [])

    if components is None:
        components = []

    if not isinstance(components, list):
        fail(
            "Asset manifest 'components' must be an array."
        )

    for index, component in enumerate(components):
        if not isinstance(component, dict):
            fail(
                f"Component entry #{index} "
                "must be a JSON object."
            )

        config = component.get("config")

        if isinstance(config, str) and config.strip():
            paths.append(config.strip())

    #
    # Preserve order while removing duplicates.
    #
    unique_paths: list[str] = []
    seen: set[str] = set()

    for path in paths:
        if path in seen:
            continue

        seen.add(path)
        unique_paths.append(path)

    return unique_paths


def create_json_placeholder(
    file_path: Path,
    force: bool,
) -> str:
    if file_path.exists() and not force:
        return "skipped"

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    #
    # Use a valid empty JSON object instead of a zero-byte file.
    #
    file_path.write_text(
        "{}\n",
        encoding="utf-8",
    )

    return "created"


def create_asset_skeleton(
    manifest_file: Path,
    force: bool,
) -> None:
    manifest = load_manifest(
        manifest_file
    )

    config_paths = collect_config_paths(
        manifest
    )

    if not config_paths:
        print(
            "No referenced configuration files found."
        )
        return

    #
    # All relative paths in the manifest are resolved
    # against the directory containing the manifest.
    #
    manifest_dir = manifest_file.resolve().parent

    created_count = 0
    skipped_count = 0

    print(
        f"Asset manifest: {manifest_file}"
    )

    print(
        f"Base directory:  {manifest_dir}"
    )

    print()

    for config_path in config_paths:
        path = Path(config_path)

        if path.is_absolute():
            target_path = path
        else:
            target_path = (
                manifest_dir / path
            ).resolve()

        status = create_json_placeholder(
            target_path,
            force,
        )

        if status == "created":
            print(
                f"CREATE  {target_path}"
            )
            created_count += 1
        else:
            print(
                f"SKIP    {target_path}"
            )
            skipped_count += 1

    print()

    print(
        f"Created: {created_count}"
    )

    print(
        f"Skipped: {skipped_count}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create placeholder configuration files "
            "referenced by a Hakoniwa asset manifest."
        )
    )

    parser.add_argument(
        "manifest",
        type=Path,
        help=(
            "Path to the Hakoniwa asset manifest JSON file."
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Overwrite existing referenced configuration files."
        ),
    )

    args = parser.parse_args()

    if not args.manifest.is_file():
        fail(
            f"Asset manifest not found: "
            f"{args.manifest}"
        )

    create_asset_skeleton(
        manifest_file=args.manifest,
        force=args.force,
    )


if __name__ == "__main__":
    main()
