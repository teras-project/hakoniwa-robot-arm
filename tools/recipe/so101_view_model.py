"""SO-101 view-models for a Hakoniwa viewer (e.g. hakoniwa-threejs-drone).

From the forged SO-101 MJCFs, writes one GLB per body and the view-model JSON
with the tools of hakoniwa-mbody-registry (a sibling checkout), for the arm
(so101.xml, recipes/so101/viewer/viewer.recipe.yaml) and for the cube to grasp
(so101.environment.xml, recipes/so101/viewer/grasp_cube.recipe.yaml):

  <output>/<name>/model.xml          the MJCF, mesh names and paths made explicit
  <output>/<name>/parts/<body>.glb   one GLB per body (mjcf2glb.py --split-by body --visible-only)
  <output>/<name>/viewer.recipe.yaml the recipe
  <output>/<name>/view-model.json    hako_viewer_model_gen.py, checked by validate_view_model.py
  <output>/environment/              the scenery (floor, sensor housing) as GLBs in the three.js
                                     frame, and environment.json (body name, position)

The MJCF copy is made for mjcf2glb.py (viewer_copy): it reads neither MuJoCo's
default mesh names and meshdir nor materials, default classes or planes.
Needs trimesh, numpy and PyYAML.

python3 tools/recipe/so101_view_model.py
"""
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _hakoniwa_composer import workspace_work_dir  # noqa: E402

ARM_ROOT = Path(__file__).resolve().parents[2]
FLOOR_HALF_THICKNESS = 0.002
FLOOR_RGBA = "0.11 0.24 0.41 1"  # the floor's checker texture, averaged


def viewer_copy(source: Path) -> str:
    """The MJCF as mjcf2glb.py reads it: each <mesh> named after its file and
    given its full path (as MuJoCo resolves them), each visual geom given its
    material's colour, the collision geoms left out (they overlap the visual
    ones), and a plane made a thin box (mjcf2glb.py draws no planes)."""
    root = ET.parse(source).getroot()
    compiler = root.find("compiler")
    meshdir = source.parent / (compiler.get("meshdir", "") if compiler is not None else "")
    for mesh in root.iter("mesh"):
        file = mesh.get("file")
        if file:
            mesh.set("name", mesh.get("name") or Path(file).stem)
            mesh.set("file", str((meshdir / file).resolve()))
    colours = {m.get("name"): m.get("rgba") for m in root.iter("material") if m.get("rgba")}
    for parent in root.iter():
        for geom in list(parent.findall("geom")):
            if geom.get("class") == "collision":
                parent.remove(geom)
                continue
            if geom.get("rgba") is None and geom.get("material") in colours:
                geom.set("rgba", colours[geom.get("material")])
            if geom.get("type") == "plane":
                sx, sy = geom.get("size", "1 1").split()[:2]
                geom.set("type", "box")
                geom.set("size", f"{sx} {sy} {FLOOR_HALF_THICKNESS}")
                geom.set("pos", f"0 0 {-FLOOR_HALF_THICKNESS}")
                geom.set("rgba", geom.get("rgba") or FLOOR_RGBA)
    return ET.tostring(root, encoding="unicode")


def environment_bodies(source: Path) -> list[dict]:
    """The static scenery of the environment MJCF: the world's own geoms
    (worldbody, the floor) and each body without a joint that is not the arm."""
    root = ET.parse(source).getroot()
    world = root.find("worldbody")
    bodies = [{"name": "worldbody", "pos": [0.0, 0.0, 0.0]}]
    for body in world.findall("body"):
        if body.get("name") in ("base", "grasp_cube") or body.find("joint") is not None \
                or body.find("freejoint") is not None:
            continue
        pos = [float(v) for v in body.get("pos", "0 0 0").split()]
        bodies.append({"name": body.get("name"), "pos": pos})
    return bodies


def main() -> int:
    work = workspace_work_dir()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", type=Path, default=work / "model-forge/so101/install/so101.xml")
    parser.add_argument("--environment-model", type=Path,
                        default=work / "model-forge/so101/install/so101.environment.xml")
    parser.add_argument("--output", type=Path, default=work / "model-forge/so101/viewer")
    parser.add_argument("--registry", type=Path, default=ARM_ROOT.parent / "hakoniwa-mbody-registry")
    args = parser.parse_args()
    tools = args.registry / "tools"
    if not (tools / "mjcf2glb.py").is_file():
        raise SystemExit(f"hakoniwa-mbody-registry not found: {args.registry}")

    def run(tool: str, *tool_args: object) -> None:
        # From the registry root, as its own body tools run (the validator finds its schema there).
        subprocess.run([sys.executable, str(tools / tool), *(str(a) for a in tool_args)],
                       cwd=args.registry, check=True)

    # Only this tool's own folders: so101_viewer_config.py writes beside them.
    for name in ("so101", "grasp_cube", "environment"):
        if (args.output / name).exists():
            shutil.rmtree(args.output / name)
    for name, model, recipe in (("so101", args.model, "viewer.recipe.yaml"),
                                ("grasp_cube", args.environment_model, "grasp_cube.recipe.yaml")):
        out = args.output / name
        (out / "parts").mkdir(parents=True)
        (out / "model.xml").write_text(viewer_copy(model), encoding="utf-8")
        shutil.copyfile(ARM_ROOT / "recipes/so101/viewer" / recipe, out / "viewer.recipe.yaml")
        run("mjcf2glb.py", out / "model.xml", "--output-dir", out / "parts", "--split-by", "body", "--visible-only")
        run("hako_viewer_model_gen.py", out / "viewer.recipe.yaml", "--out", out / "view-model.json", "--pretty")
        run("validate_view_model.py", out / "view-model.json")
        print(f"written: {out / 'view-model.json'}")

    # The scenery (floor, sensor housing): GLBs in the viewer's (three.js) frame
    # and where they stand (ROS frame), for the scene's environments.
    out = args.output / "environment"
    (out / "parts").mkdir(parents=True)
    (out / "model.xml").write_text(viewer_copy(args.environment_model), encoding="utf-8")
    run("mjcf2glb.py", out / "model.xml", "--output-dir", out / "parts", "--split-by", "body", "--visible-only",
        "--target-frame", "threejs")
    scenery = [body for body in environment_bodies(args.environment_model)
               if (out / "parts" / f"{body['name']}.glb").is_file()]
    (out / "environment.json").write_text(json.dumps(scenery, indent=2) + "\n", encoding="utf-8")
    print(f"written: {out / 'environment.json'} ({', '.join(b['name'] for b in scenery)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
