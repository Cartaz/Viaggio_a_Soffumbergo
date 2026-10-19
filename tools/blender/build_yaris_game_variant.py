"""Keep the stock reference intact; cut the game's real mast passage separately.

Run after build_yaris.py, with Blender 4.5 in background mode.
The collar and opening are fictional game parts, not Toyota equipment.
"""
from pathlib import Path
import json
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_yaris as build


def main():
    bpy.ops.wm.open_mainfile(filepath=str(build.SOURCE / "yaris_trend_2022.blend"))
    build.CAR = bpy.data.objects["YarisTrend2022"]
    build.GROUP = bpy.data.objects["Body"]
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.45))
    cutter = bpy.context.object
    cutter.name = "Temporary mast aperture cutter"
    cutter.scale = (.32, .32, .40)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    for name in ["Stock painted roof", "Roof headlining"]:
        obj = bpy.data.objects[name]
        bpy.context.view_layer.objects.active = obj
        if name == "Roof headlining":
            obj.modifiers.new("Headliner thickness", "SOLIDIFY").thickness = .008
        for mod in list(obj.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
        mod = obj.modifiers.new("Physical mast passage", "BOOLEAN")
        mod.operation = "DIFFERENCE"
        mod.solver = "EXACT"
        mod.object = cutter
        bpy.ops.object.modifier_apply(modifier=mod.name)
        tree = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
        assert tree.ray_cast(Vector((0, 0, 1.7)), Vector((0, 0, -1)), .4)[0] is None
        assert tree.ray_cast(Vector((.24, 0, 1.7)), Vector((0, 0, -1)), .4)[0] is not None
    bpy.data.objects.remove(cutter, do_unlink=True)
    # Relocate the dome light clear of the actual aperture.
    for name in ["Roof lamp console", "Dome light lens"]:
        bpy.data.objects[name].location.y = -.32
    bpy.data.objects["MastRoof"].location.y = 0
    steel = bpy.data.materials["Brake_and_structural_metal"]
    for side in [-1, 1]:
        build.box("Fictional roof aperture collar", (.38, .022, .012), (0, side * .171, 1.504), steel, .004)
        build.box("Fictional roof aperture collar", (.022, .32, .012), (side * .171, 0, 1.504), steel, .004)
    build.CAR["variant"] = "fictional mast aperture; not standard Toyota bodywork"
    build.apply_and_merge()
    build.export_glb(build.OUT / "yaris_trend_2022_game.glb")
    (build.REPORT / "roof_passage_check.json").write_text(json.dumps({
        "opening_m": [.32, .32], "roof_and_headliner_center_rays_clear": True,
        "roof_and_headliner_adjacent_rays_hit": True,
        "structural_certification": False}, indent=2) + "\n", encoding="utf8")
    print("YARIS_GAME_VARIANT_COMPLETE")


if __name__ == "__main__":
    main()
