"""SO-101 view-model for a Hakoniwa viewer (e.g. hakoniwa-threejs-drone).

From the forged SO-101 MJCF, writes one GLB per body and the view-model JSON
with the tools of hakoniwa-mbody-registry (a sibling checkout):

  <output>/model.xml          the MJCF, mesh names and paths made explicit
  <output>/parts/<body>.glb   one GLB per body (mjcf2glb.py --split-by body --visible-only)
  <output>/viewer.recipe.yaml recipes/so101/viewer/viewer.recipe.yaml
  <output>/view-model.json    hako_viewer_model_gen.py, checked by validate_view_model.py

The forged MJCF names its meshes after their files and finds them in meshdir,
as MuJoCo does; mjcf2glb.py needs the names and the paths written out, so the
copy has them. Needs trimesh, numpy and PyYAML.

python3 tools/recipe/so101_view_model.py
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hakoniwa_composer import workspace_work_dir  # noqa: E402

ARM_ROOT = Path(__file__).resolve().parents[2]


def explicit_meshes(source: Path) -> str:
    """The MJCF with each <mesh> named after its file and given its full path."""
    text = source.read_text(encoding="utf-8")
    found = re.search(r'meshdir="([^"]+)"', text)
    meshdir = (source.parent / found.group(1)) if found else source.parent

    def mesh(match: re.Match) -> str:
        attributes = match.group(1)
        file = re.search(r'file="([^"]+)"', attributes).group(1)
        path = (meshdir / file).resolve()
        attributes = attributes.replace(f'file="{file}"', f'file="{path}"')
        if "name=" not in attributes:
            attributes = f' name="{Path(file).stem}"' + attributes
        return f"<mesh{attributes}"

    return re.sub(r"<mesh((?:\s+[a-z_]+=\"[^\"]*\")+)", mesh, text)


def main() -> int:
    work = workspace_work_dir()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", type=Path, default=work / "model-forge/so101/install/so101.xml")
    parser.add_argument("--output", type=Path, default=work / "model-forge/so101/viewer")
    parser.add_argument("--registry", type=Path, default=ARM_ROOT.parent / "hakoniwa-mbody-registry")
    args = parser.parse_args()
    tools = args.registry / "tools"
    if not (tools / "mjcf2glb.py").is_file():
        raise SystemExit(f"hakoniwa-mbody-registry not found: {args.registry}")
    if args.output.exists():
        shutil.rmtree(args.output)
    (args.output / "parts").mkdir(parents=True)
    (args.output / "model.xml").write_text(explicit_meshes(args.model), encoding="utf-8")
    shutil.copyfile(ARM_ROOT / "recipes/so101/viewer/viewer.recipe.yaml", args.output / "viewer.recipe.yaml")

    def run(tool: str, *tool_args: object) -> None:
        # From the registry root, as its own body tools run (the validator finds its schema there).
        subprocess.run([sys.executable, str(tools / tool), *(str(a) for a in tool_args)],
                       cwd=args.registry, check=True)

    run("mjcf2glb.py", args.output / "model.xml", "--output-dir", args.output / "parts",
        "--split-by", "body", "--visible-only")
    run("hako_viewer_model_gen.py", args.output / "viewer.recipe.yaml", "--out", args.output / "view-model.json",
        "--pretty")
    run("validate_view_model.py", args.output / "view-model.json")
    print(f"written: {args.output / 'view-model.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
