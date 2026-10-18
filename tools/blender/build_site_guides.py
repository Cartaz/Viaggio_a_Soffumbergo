"""Flat, source-linked survey guides. NOT terrain or reconstructed buildings.

blender --background --factory-startup --python tools/blender/build_site_guides.py -- --output art/source/generated/valle_guides.blend
Requires Blender; prepared but not run here. Existing output is preserved.
"""
import argparse
import json
from pathlib import Path
import sys
import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from coffa.geography import to_godot


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / "art/source/generated/valle_guides.blend")
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(args.output)
    data = json.loads((ROOT / "data/geography/osm_survey.geojson").read_text())
    collection = bpy.data.collections.new("VALLE_2D_GUIDES_NO_HEIGHTS")
    bpy.context.scene.collection.children.link(collection)
    origin = [13.3930177, 46.1568367, 0]
    for f in data["features"]:
        p = f["properties"]
        g = f["geometry"]
        if "building" not in p or g["type"] != "Polygon":
            continue
        coords = g["coordinates"][0][:-1]
        verts = []
        for c in coords:
            east, _, south = to_godot([c[0], c[1], 0], origin)
            verts.append((east, -south, 0))  # Flat guide only; never a terrain elevation.
        mesh = bpy.data.meshes.new(f"OSM footprint {p['osm_id']}")
        mesh.from_pydata(verts, [(i, (i + 1) % len(verts)) for i in range(len(verts))], [])
        mesh.update()
        obj = bpy.data.objects.new(p.get("name", f"OSM building {p['osm_id']}"), mesh)
        obj["source_url"] = f"https://www.openstreetmap.org/way/{p['osm_id']}"
        obj["status"] = "2D_GUIDE_NOT_RECONSTRUCTION"
        obj["height_status"] = "UNKNOWN"
        collection.objects.link(obj)
    bpy.context.scene.unit_settings.system = "METRIC"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    print("Saved flat guides, no heights or facade geometry:", args.output)


if __name__ == "__main__":
    main()
