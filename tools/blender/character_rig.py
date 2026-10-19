"""Deterministic deformation rig, garment weights and ear clearance for Blender 4.5."""
import math

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


def headwear_clearance(character):
    """Shrink around the headwear centre and carve clearance around both ears."""
    head_z = character.config["head_z"]
    centre = Vector((0, .012, head_z + .105))
    hats = [o for o in character.objects if o.name.split("_", 1)[1].startswith(
        ("beret", "cap_", "flat_cap"))]
    for obj in hats:
        if obj.type == "CURVE":
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.convert(target="MESH")
        world = obj.matrix_world.copy()
        inv = world.inverted()
        for v in obj.data.vertices:
            p = world @ v.co
            p = centre + Vector(((p.x - centre.x) * .89,
                                 (p.y - centre.y) * .90,
                                 (p.z - centre.z) * .91)) + Vector((0, 0, .008))
            v.co = inv @ p
    for side in (-1, 1):
        ear = next(o for o in character.objects if o.name.endswith(f"ear_outer_{side}"))
        # Inflate the actual ear mesh, so the resulting pocket follows its shape.
        cutter = ear.copy()
        cutter.data = ear.data.copy()
        character.collection.objects.link(cutter)
        cutter.scale = (1.11, 1.30, 1.10)
        bpy.context.view_layer.update()
        for hat in hats:
            mod = hat.modifiers.new("Ear pocket 6 mm clearance", "BOOLEAN")
            mod.operation, mod.solver, mod.object = "DIFFERENCE", "EXACT", cutter
            bpy.context.view_layer.objects.active = hat
            bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    overlaps = 0
    for hat in hats:
        a = BVHTree.FromObject(hat, graph)
        for side in (-1, 1):
            ear = next(o for o in character.objects if o.name.endswith(f"ear_outer_{side}"))
            # BVHs use object-local coordinates: both meshes are transformed to world.
            hm = hat.evaluated_get(graph).to_mesh()
            em = ear.evaluated_get(graph).to_mesh()
            hv = [hat.matrix_world @ v.co for v in hm.vertices]
            ev = [ear.matrix_world @ v.co for v in em.vertices]
            hb = BVHTree.FromPolygons(hv, [list(p.vertices) for p in hm.polygons])
            eb = BVHTree.FromPolygons(ev, [list(p.vertices) for p in em.polygons])
            overlaps += len(hb.overlap(eb))
            hat.evaluated_get(graph).to_mesh_clear()
            ear.evaluated_get(graph).to_mesh_clear()
    if overlaps:
        raise ValueError(f"{character.key}: hat/ear intersections: {overlaps}")
    character.root["hat_ear_intersections"] = overlaps
    character.root["headwear_scale_xy"] = .89


def rig_character(c):
    bpy.context.view_layer.update()
    headwear_clearance(c)
    # Flatten the previous head pivot into rest-space mesh coordinates.
    meshes = []
    for obj in c.objects:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        if obj.type == "CURVE":
            bpy.ops.object.convert(target="MESH")
        world = obj.matrix_world.copy()
        obj.parent = c.root
        obj.matrix_world = world
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        meshes.append(obj)
    for obj in list(c.collection.objects):
        if obj.type == "EMPTY" and obj != c.root:
            bpy.data.objects.remove(obj, do_unlink=True)
    data = bpy.data.armatures.new(c.key + "_Skeleton")
    arm = bpy.data.objects.new(c.key + "_Rig", data)
    c.collection.objects.link(arm)
    arm.parent = c.root
    arm.show_in_front = True
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")

    def bone(name, a, b, parent=None):
        part = data.edit_bones.new(name)
        part.head, part.tail = a, b
        if parent:
            part.parent = data.edit_bones[parent]
        return part

    bone("pelvis", (0, 0, .255), (0, 0, .345))
    bone("spine", (0, 0, .345), (0, .008, .52), "pelvis")
    hz = c.config["head_z"]
    bone("head", (0, .015, hz - .065), (0, .015, hz + .04), "spine")
    bone("tail", (0, -.09, .23), (.08, -.27, .14), "pelvis")
    for side, (shoulder, elbow, wrist, hip, knee, foot) in c.limb_joints.items():
        bone(f"upper_arm_{side}", shoulder, elbow, "spine")
        bone(f"forearm_{side}", elbow, wrist, f"upper_arm_{side}")
        bone(f"hand_{side}", wrist, wrist + Vector((0, .008, -.06)), f"forearm_{side}")
        bone(f"thigh_{side}", hip, knee, "pelvis")
        bone(f"shin_{side}", knee, foot, f"thigh_{side}")
        bone(f"foot_{side}", foot, foot + Vector((0, .075, 0)), f"shin_{side}")
        bone(f"cape_{side}", (side * .11, -.015, .51), (side * .15, -.025, .35), "spine")
        for digit in range(4):
            a, b, tip = c.finger_joints[(side, digit)]
            bone(f"finger_{side}_{digit}_a", a, b, f"hand_{side}")
            bone(f"finger_{side}_{digit}_b", b, tip, f"finger_{side}_{digit}_a")
    bone("cape_back", (0, -.07, .51), (0, -.12, .35), "spine")
    bpy.ops.object.mode_set(mode="OBJECT")
    head_names = ("head", "nose", "ear_", "eye_", "pupil", "upper_lid", "lash",
                  "brow", "smile", "whisker", "beret", "cap_", "flat_cap")
    for obj in meshes:
        name = obj.name[len(c.key) + 1:]
        groups = {b.name: obj.vertex_groups.new(name=b.name) for b in data.bones}
        rigid = "spine"
        if name.startswith(head_names):
            rigid = "head"
        elif name == "tail":
            rigid = "tail"
        for side in (-1, 1):
            if name in [f"upper_arm_{side}", f"sleeve_{side}"]:
                rigid = f"upper_arm_{side}"
            elif name == f"forearm_{side}":
                rigid = f"forearm_{side}"
            elif name.endswith(f"_{side}") and name.startswith(("palm", "small_thumb", "thumb_claw")):
                rigid = f"hand_{side}"
            elif name == f"thigh_{side}":
                rigid = f"thigh_{side}"
            elif name == f"shin_{side}":
                rigid = f"shin_{side}"
            elif name == f"heel_{side}" or name == f"instep_{side}" or name.startswith(f"toe_") and f"_{side}_" in name:
                rigid = f"foot_{side}"
            for digit in range(4):
                if name == f"finger_proximal_{side}_{digit}":
                    rigid = f"finger_{side}_{digit}_a"
                elif name in [f"finger_knuckle_{side}_{digit}", f"finger_distal_{side}_{digit}", f"finger_claw_{side}_{digit}"]:
                    rigid = f"finger_{side}_{digit}_b"
        for v in obj.data.vertices:
            if name == "purple_cape":
                free = max(0, min(1, (.55 - v.co.z) / .16))
                lateral = min(1, abs(v.co.x) / .13)
                side = 1 if v.co.x >= 0 else -1
                arm_weight = free * lateral * .60
                cape_weight = free * .30
                groups[f"upper_arm_{side}"].add([v.index], arm_weight, "REPLACE")
                groups[f"cape_{side}" if lateral > .35 else "cape_back"].add([v.index], cape_weight, "REPLACE")
                groups["spine"].add([v.index], 1 - arm_weight - cape_weight, "REPLACE")
            elif name in ("body", "red_sweater", "ribbed_hem", "picnic_dress", "neck"):
                weight = max(0, min(1, (v.co.z - .28) / .19))
                groups["spine"].add([v.index], weight, "REPLACE")
                groups["pelvis"].add([v.index], 1 - weight, "REPLACE")
            else:
                groups[rigid].add([v.index], 1, "REPLACE")
        mod = obj.modifiers.new("Character deformation", "ARMATURE")
        mod.object = arm
        obj.parent = arm
        # Remove empty vertex groups to keep the exported skin compact.
        used = {g.group for v in obj.data.vertices for g in v.groups if g.weight > 0}
        for group in list(obj.vertex_groups)[::-1]:
            if group.index not in used:
                obj.vertex_groups.remove(group)
    c.armature = arm
    c.root["status"] = "SKINNED_PHYSICS_ANIMATION_RIG"
    c.root["bone_count"] = len(data.bones)
    c.objects = meshes
    bpy.context.view_layer.update()
