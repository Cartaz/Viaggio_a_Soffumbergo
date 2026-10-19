"""Non-destructive collection generator for Blender 4.5 LTS (not executed here).

blender --background --factory-startup --python tools/blender/build_blockout.py -- --output art/source/generated
Produces fit/proportion proxies, NOT a faithful final Yaris or approved mouse.
Blender axes: X right, Y forward, Z up. glTF export converts to Godot X/Y/-Z.
"""
import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_characters import Character  # noqa: E402


def material(name, color, metallic=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    shader = m.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = 0.65
    shader.inputs["Metallic"].default_value = metallic
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, default=ROOT / "art/source/generated")
    p.add_argument("--overwrite", action="store_true")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = p.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    outputs = [args.output / "fit_blockout.blend", args.output / "fit_blockout.glb"]
    if not args.overwrite and any(f.exists() for f in outputs):
        raise FileExistsError("Generated output exists; use --overwrite explicitly")
    config = json.loads((ROOT / "data/config/vehicle_lab.json").read_text())
    rig = json.loads((ROOT / "data/config/mouse_rig.json").read_text())
    collection = bpy.data.collections.new("SOFFUMBERGO_FIT_ONLY")
    bpy.context.scene.collection.children.link(collection)
    generated = []

    def register(obj, name, mat):
        obj.name = name
        for previous in list(obj.users_collection):
            previous.objects.unlink(obj)
        collection.objects.link(obj)
        obj.data.materials.append(mat)
        obj["asset_status"] = "PROXY_NOT_FINAL"
        generated.append(obj)
        return obj

    def box(name, size, at, mat, bevel=0.02):
        bpy.ops.mesh.primitive_cube_add(size=1, location=at)
        obj = register(bpy.context.object, name, mat)
        obj.scale = size
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        if bevel:
            mod = obj.modifiers.new("Soft proxy edges", "BEVEL")
            mod.width = bevel
            mod.segments = 3
            obj.modifiers.new("Weighted proxy normals", "WEIGHTED_NORMAL")
        return obj

    def ellipsoid(name, radii, at, mat):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=1, location=at)
        obj = register(bpy.context.object, name, mat)
        obj.scale = radii
        for face in obj.data.polygons:
            face.use_smooth = True
        return obj

    def rod(name, start, end, radius, mat):
        a, b = Vector(start), Vector(end)
        direction = b - a
        bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=radius,
                                           depth=direction.length, location=(a + b) / 2)
        obj = register(bpy.context.object, name, mat)
        obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
        obj.rotation_mode = "QUATERNION"
        # Assign again after changing rotation mode, keeping orientation explicit.
        obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
        return obj

    red = material("Trend red — colour placeholder", (0.62, 0.035, 0.05))
    rubber = material("Tyres", (0.025, 0.035, 0.04))
    glass = material("Standard non-privacy glass proxy", (0.25, 0.43, 0.46))
    alloy = material("16 inch alloy proxy", (0.46, 0.5, 0.53), 0.6)
    wood = material("Mast and nest", (0.46, 0.29, 0.13))
    metal = material("Pedal linkage", (0.28, 0.31, 0.32), 0.5)
    trim = material("Black cloth", (0.07, 0.075, 0.075))

    # Body envelope only; avoid inventing exact MY22 bodywork from primitives.
    box("Yaris envelope 3940x1745", (1.745, 3.94, 0.58), (0, 0, 0.72), red, 0.12)
    box("Cabin glazing proxy", (1.44, 1.86, 0.45), (0, -0.05, 1.21), glass, 0.10)
    # Four separate roof strips leave a real gap; no black fake-hole decal.
    box("Roof left", (0.55, 1.80, 0.07), (-0.42, -0.05, 1.465), red)
    box("Roof right", (0.55, 1.80, 0.07), (0.42, -0.05, 1.465), red)
    box("Roof front", (0.30, 0.65, 0.07), (0, 0.51, 1.465), red)
    box("Roof rear", (0.30, 0.65, 0.07), (0, -0.61, 1.465), red)
    # Also split the glazing block around the mast passage using a Boolean.
    cutter = box("Temporary roof passage cutter", (0.30, 0.30, 2.0), (0, 0, 1.0), metal, 0)
    cabin = next(o for o in generated if o.name.startswith("Cabin glazing"))
    modifier = cabin.modifiers.new("Actual mast opening", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.object = cutter
    bpy.context.view_layer.objects.active = cabin
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    generated.remove(cutter)
    bpy.data.objects.remove(cutter, do_unlink=True)

    track = config["body"]["track_m"]
    for side in (-1, 1):
        for axle in (-1, 1):
            x, y = side * track / 2, axle * 1.28
            tire = rod(f"195-55-R16 tyre {side} {axle}", (x - 0.0975, y, 0.31045),
                       (x + 0.0975, y, 0.31045), 0.31045, rubber)
            tire["nominal_tire"] = "195/55 R16; tread/sidewall pending"
            rod(f"16 inch rim {side} {axle}", (x - 0.102, y, 0.31045),
                (x + 0.102, y, 0.31045), 0.2032, alloy)
    for side in (-1, 1):
        box(f"Bodycolour mirror {side}", (0.15, 0.22, 0.12), (side * 0.88, 0.65, 1.14), red)
        box(f"Bodycolour handle proxy {side}", (0.035, 0.16, 0.035), (side * 0.88, 0.05, 0.99), red)

    rod("Mast structural core proxy", (0, 0, 0.35), (0, 0, 6.1), 0.09, wood)
    box("Mast floor anchorage proxy", (0.50, 0.50, 0.06), (0, 0, 0.39), metal)
    box("Nest deck", (1.20, 1.20, 0.12), (0, 0, 5.6), wood)
    for side in (-1, 1):
        for axis in (0, 1):
            at = [0, 0, 5.95]
            at[axis] = side * 0.56
            size = [1.2, 0.06, 0.10] if axis == 1 else [0.06, 1.2, 0.10]
            box(f"Nest rail {axis} {side}", size, at, wood)
    for height in range(10, 57, 2):
        z = height / 10
        rod("Climbing rung", (-0.19, -0.14, z), (0.19, -0.14, z), 0.018, metal)

    characters = json.loads((ROOT / "data/config/characters.json").read_text(encoding="utf-8"))
    for key, centre in (("Bernie", (-0.32, 0.35, 0.63)), ("Bianca", (0.10, 0.10, 5.66))):
        character = Character(key, characters["characters"][key], rig).build()
        character.root.location = centre
        character.root.scale = (float(rig["uniform_scale"]),) * 3
        generated.extend(character.collection.objects)
    # Neutral design poses: seated rig, wheel/pedal contact and climbing remain pending.
    box("Raised black cloth fit seat", (0.45, 0.60, 0.12), (-0.32, 0.22, 0.61), trim)
    # Mechanical concept: reachable small pads connect to original pedal locations.
    # Rod geometry is a layout, not a solved/animated four-bar mechanism.
    for i in range(2):
        x = -0.43 + i * 0.20
        box("Paw-sized pedal extension", (0.09, 0.12, 0.025), (x, 0.60, 0.75), metal)
        rod("Pedal extension linkage", (x, 0.60, 0.73), (x, 0.96, 0.30), 0.012, metal)
        rod("Pedal pivot", (x - 0.06, 0.75, 0.47), (x + 0.06, 0.75, 0.47), 0.018, metal)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in generated:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = generated[0]
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 1
    bpy.ops.wm.save_as_mainfile(filepath=str(outputs[0].resolve()))
    bpy.ops.export_scene.gltf(filepath=str(outputs[1].resolve()), export_format="GLB",
                              use_selection=True, export_apply=True, export_yup=True)
    print("Generated fit proxies only:", outputs)


if __name__ == "__main__":
    main()
