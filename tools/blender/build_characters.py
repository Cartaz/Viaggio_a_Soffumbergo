"""Build the Bianca / Bernie character studies, GLBs and actual Blender renders.

Blender 4.5 LTS. X right, Y forward, Z up; GLB converts to Godot axes.
New user direction 2026-10-19: biped silhouettes, Bianca more slender.
Skinned rigs for physics-driven driving/bracing; exploration gait remains pending.
No external images/textures are embedded. Palette is an artistic approximation.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character_rig import rig_character

ROOT = Path(__file__).resolve().parents[2]


def material(name, color, roughness=0.65):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Roughness"].default_value = roughness
    return mat


class Character:
    def __init__(self, key, config, rig):
        self.key, self.config, self.rig = key, config, rig
        self.collection = bpy.data.collections.new(key)
        bpy.context.scene.collection.children.link(self.collection)
        self.root = bpy.data.objects.new(key, None)
        self.collection.objects.link(self.root)
        self.root["role"] = config["role"]
        self.root["status"] = "DESIGN_MODEL_NOT_SKINNED"
        self.root["locomotion_direction"] = "biped"
        self.objects = []
        self.limb_joints = {}
        self.finger_joints = {}
        self.mats = {k: material(key + "_" + k, v)
                     for k, v in config["palette"].items()}

    def register(self, obj, name, mat):
        obj.name = self.key + "_" + name
        for previous in list(obj.users_collection):
            previous.objects.unlink(obj)
        self.collection.objects.link(obj)
        obj.parent = self.root
        obj.data.materials.append(self.mats[mat])
        self.objects.append(obj)
        if obj.type == "MESH":
            for face in obj.data.polygons:
                face.use_smooth = True
        return obj

    def ell(self, name, at, radii, mat):
        small = max(radii) < .035
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16 if small else 32,
                                           ring_count=10 if small else 20,
                                           radius=1, location=at)
        obj = self.register(bpy.context.object, name, mat)
        obj.scale = radii
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        return obj

    def mesh(self, name, verts, faces, mat, thickness=0):
        mesh = bpy.data.meshes.new(self.key + "_" + name)
        mesh.from_pydata(verts, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        self.collection.objects.link(obj)
        self.register(obj, name, mat)
        if thickness:
            solid = obj.modifiers.new("Cloth thickness", "SOLIDIFY")
            solid.thickness = thickness
            solid.offset = 0
        return obj

    def line(self, name, points, radius, mat):
        curve = bpy.data.curves.new(self.key + "_" + name, "CURVE")
        curve.dimensions = "3D"
        curve.resolution_u = 12
        curve.bevel_depth = radius
        curve.bevel_resolution = 3
        spline = curve.splines.new("BEZIER")
        spline.bezier_points.add(len(points) - 1)
        for bp, point in zip(spline.bezier_points, points):
            bp.co = point
            bp.handle_left_type = "AUTO"
            bp.handle_right_type = "AUTO"
        obj = bpy.data.objects.new(name, curve)
        self.collection.objects.link(obj)
        self.register(obj, name, mat)
        return obj

    def segment(self, name, a, b, radius, mat):
        direction = Vector(b) - Vector(a)
        obj = self.ell(name, (Vector(a) + Vector(b)) / 2,
                       (radius, radius, direction.length / 2 + radius * .4), mat)
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = direction.to_track_quat("Z", "Y")
        return obj

    def garment(self, name, rings, mat, opening=0):
        # rings = (z, x radius, y radius, y offset). Separate open garment mesh.
        if name == "purple_cape":
            dense = []
            for a, b in zip(rings, rings[1:]):
                steps = math.ceil(abs(b[0] - a[0]) / .010)
                for step in range(steps):
                    t = step / steps
                    dense.append(tuple(x * (1-t) + y * t for x, y in zip(a, b)))
            rings = dense + [rings[-1]]
        verts, faces, count = [], [], 48 if name == "purple_cape" else 64
        stride = count + 1 if opening else count
        for z, rx, ry, cy in rings:
            for i in range(stride):
                angle = opening + (2 * math.pi - 2 * opening) * i / count
                verts.append((rx * math.sin(angle), cy + ry * math.cos(angle), z))
        for row in range(len(rings) - 1):
            for i in range(count):
                a = row * stride + i
                b = row * stride + (i + 1) % stride
                faces.append((a, b, b + stride, a + stride))
        return self.mesh(name, verts, faces, mat, .004)

    def paws(self, side, wrist, ankle, slender):
        """Separate tapered digits, knuckles and small claws, rather than mittens."""
        size = .92 if slender else 1.0
        palm = wrist + Vector((0, .003, -.010))
        self.ell(f"palm_{side}", palm, (.017 * size, .012, .023), "paw")
        for digit, (spread, length) in enumerate(zip((-.012, -.004, .005, .013),
                                                    (.023, .029, .028, .021))):
            base = palm + Vector((side * spread, .002, -.014))
            knuckle = base + Vector((side * spread * .17, .006, -length * .48))
            tip = knuckle + Vector((side * spread * .13, .007, -length * .52))
            self.finger_joints[(side, digit)] = (base, knuckle, tip)
            self.segment(f"finger_proximal_{side}_{digit}", base, knuckle, .0040 * size, "paw")
            self.ell(f"finger_knuckle_{side}_{digit}", knuckle, (.0042, .0045, .0045), "paw")
            self.segment(f"finger_distal_{side}_{digit}", knuckle, tip, .0032 * size, "paw")
            nail = self.ell(f"finger_claw_{side}_{digit}", tip + Vector((0, .003, -.003)),
                            (.0023, .0026, .0050), "claw")
            nail.rotation_euler.x = -.35
        thumb_a = palm + Vector((-side * .014, .002, .003))
        thumb_b = palm + Vector((-side * .025, .011, -.010))
        self.segment(f"small_thumb_{side}", thumb_a, thumb_b, .0048 * size, "paw")
        self.ell(f"thumb_claw_{side}", thumb_b + Vector((0, .003, -.002)),
                 (.0024, .0030, .0038), "claw")
        # Narrow heel / instep and splayed toes with independent curved tips.
        self.ell(f"heel_{side}", ankle + Vector((0, .005, .010)),
                 (.022 * size, .026, .018), "paw")
        self.ell(f"instep_{side}", ankle + Vector((0, .028, .009)),
                 (.027 * size, .035, .016), "paw")
        for digit, (spread, length) in enumerate(zip((-.023, -.012, 0, .012, .023),
                                                    (.028, .039, .043, .039, .028))):
            base = ankle + Vector((side * spread * .85, .041, .010))
            knuckle = base + Vector((side * spread * .15, length * .50, .001))
            tip = knuckle + Vector((side * spread * .12, length * .50, -.005))
            self.segment(f"toe_proximal_{side}_{digit}", base, knuckle, .0054 * size, "paw")
            self.ell(f"toe_knuckle_{side}_{digit}", knuckle, (.0058, .0065, .0055), "paw")
            self.segment(f"toe_distal_{side}_{digit}", knuckle, tip, .0043 * size, "paw")
            nail = self.ell(f"toe_claw_{side}_{digit}", tip + Vector((0, .005, -.001)),
                            (.0030, .0060, .0024), "claw")
            nail.rotation_euler.x = -.18

    def build(self):
        cfg = self.config
        slender = self.key == "Bianca"
        width, depth, height = cfg["body_radii"]
        body_z, head_z = cfg["body_z"], cfg["head_z"]
        self.ell("body", (0, 0, body_z), (width, depth, height), "fur")
        self.ell("neck", (0, .012, head_z - .12), (.071, .069, .10), "fur")
        head = self.ell("head", (0, .015, head_z), cfg["head_radii"], "fur")
        # A single continuous face replaces the conspicuous paired cheek lobes.
        lower = self.ell("face_lower", (0, .070 if slender else .073, head_z - .027),
                         (.059, .048, .043) if slender else (.072, .055, .049), "fur")
        bridge = self.ell("face_bridge", (0, .092 if slender else .100, head_z - .009),
                          (.031, .039, .027) if slender else (.038, .044, .031), "fur")
        bpy.ops.object.select_all(action="DESELECT")
        for part in (head, lower, bridge):
            part.select_set(True)
        bpy.context.view_layer.objects.active = head
        self.objects.remove(lower)
        self.objects.remove(bridge)
        bpy.ops.object.join()
        remesh = head.modifiers.new("Continuous simple face", "REMESH")
        remesh.mode = "VOXEL"
        remesh.voxel_size = .0035
        remesh.use_smooth_shade = True
        bpy.ops.object.modifier_apply(modifier=remesh.name)
        smooth = head.modifiers.new("Soft facial transitions", "SMOOTH")
        smooth.factor, smooth.iterations = .7, 5
        bpy.ops.object.modifier_apply(modifier=smooth.name)
        nose_y = .134 if slender else .147
        self.ell("nose", (0, nose_y, head_z - .007),
                 (.015, .011, .011) if slender else (.018, .013, .013), "nose")
        for side in (-1, 1):
            ear_x = side * (.112 if slender else .126)
            ear_z = head_z + .069
            self.ell(f"ear_outer_{side}", (ear_x, .005, ear_z),
                     (.068, .023, .078), "fur")
            self.ell(f"ear_inner_{side}", (ear_x, .024, ear_z + .002),
                     (.052, .009, .060), "ear")
            self.line(f"ear_fold_{side}",
                      [(ear_x, .034, ear_z - .032),
                       (ear_x - side * .018, .035, ear_z - .013),
                       (ear_x + side * .022, .033, ear_z + .020)], .0025, "muzzle")
            # Smaller, inset eyes; eyelids, pupils and glints share one proportion.
            eye_scale = float(cfg["eye_design_scale"])
            eye_x = side * (.055 if slender else .062)
            def face_surface(x, z, lift=.002):
                rx, ry, rz = cfg["head_radii"]
                rest = max(.01, 1 - (x / rx) ** 2 - ((z - head_z) / rz) ** 2)
                return .015 + ry * math.sqrt(rest) + lift
            eye = Vector((eye_x, face_surface(eye_x, head_z + .021, .001), head_z + .021))
            normal = Vector((side * .40, .9165, 0))
            tangent = Vector((side * .9165, -.40, 0))
            self.ell(f"eye_white_{side}", eye,
                     (.030 * eye_scale, .0165 * eye_scale, .038 * eye_scale), "white")
            pupil = eye + normal * (.016 * eye_scale)
            self.ell(f"pupil_{side}", pupil,
                     (.015 * eye_scale, .007 * eye_scale, .023 * eye_scale), "eyes")
            self.ell(f"eye_glint_{side}", pupil + Vector((-.005, .006, .009)) * eye_scale,
                     (.004 * eye_scale, .002 * eye_scale, .006 * eye_scale), "white")
            lid = []
            for i in range(13):
                t = math.pi * i / 12
                lid.append(eye + tangent * (.030 * eye_scale * math.cos(t))
                           + Vector((0, 0, .038 * eye_scale * math.sin(t)))
                           + normal * (.009 * eye_scale))
            self.line(f"upper_lid_{side}", lid, (.003 if slender else .0035) * eye_scale, "eyes")
            if slender:
                for i in range(3):
                    base = Vector(lid[1 + i])
                    self.line(f"lash_{side}_{i}",
                              [base, base + Vector((side * .012, .002, .009 + i * .002)) * eye_scale],
                              .0018 * eye_scale, "eyes")
            brow_z = head_z + .057
            brow_xz = [(eye_x - side * .019, brow_z + (.009 if not slender else -.004)),
                       (eye_x, brow_z + .006), (eye_x + side * .020, brow_z - .003)]
            self.line(f"brow_{side}",
                      [(x, face_surface(x, z), z) for x, z in brow_xz],
                      .0035 if not slender else .0022, "brow")
            mouth_y = .114 if slender else .124
            self.line(f"smile_{side}",
                      [(0, mouth_y, head_z - .046),
                       (side * .022, mouth_y - .004, head_z - .050),
                       (side * .044, mouth_y - .015, head_z - (.031 if slender else .040))],
                      .0011 if slender else .0014, "brow")
            for i in range(2 if slender else 3):
                self.line(f"whisker_{side}_{i}",
                          [(side * .040, mouth_y - .002, head_z - .026 - .008 * i),
                           (side * .089, mouth_y + .007, head_z - .025 + .009 * (1 - i)),
                           (side * .137, mouth_y + .001, head_z - .024 + .018 * (1 - i))],
                          .0006 if slender else .0008, "brow")
        # Limb lengths are the configuration values, never stretched for a pose.
        for side in (-1, 1):
            shoulder = Vector((side * width * .83, .003, body_z + height * .62))
            elbow = shoulder + Vector((side * .36, .28, -.89)).normalized() * self.rig["segments_m"]["upper_forelimb"]
            paw = elbow + Vector((-side * .13, .68, -.722)).normalized() * self.rig["segments_m"]["lower_forelimb"]
            hip = Vector((side * width * .49, -.012, .255))
            knee = hip + Vector((side * .10, .27, -.9576)).normalized() * self.rig["segments_m"]["upper_hindlimb"]
            foot = knee + Vector((0, -.19, -.9818)).normalized() * self.rig["segments_m"]["lower_hindlimb"]
            self.limb_joints[side] = (shoulder, elbow, paw, hip, knee, foot)
            for name, a, b, r in (("upper_arm", shoulder, elbow, .024 if slender else .031),
                                  ("forearm", elbow, paw, .020 if slender else .026),
                                  ("thigh", hip, knee, .034 if slender else .048),
                                  ("shin", knee, foot, .021 if slender else .027)):
                obj = self.segment(f"{name}_{side}", a, b, r, "fur")
                obj["joint_distance_m"] = (b - a).length
            self.paws(side, paw, foot, slender)
            # Shoulder sleeves finish above the wrist; paws remain free.
            self.segment(f"sleeve_{side}", shoulder, elbow,
                         .030 if slender else .040, "cloth")
        self.line("tail", [(0, -.09, .23), (.04, -.23, .15),
                            (.16, -.36, .08), (.22, -.46, .10), (.23, -.50, .16)],
                  .008, "ear")
        if slender:
            self.garment("picnic_dress", [(.17, .145, .120, 0), (.22, .139, .121, 0),
                                           (.31, .119, .112, 0), (.39, .117, .111, 0),
                                           (.49, .110, .105, 0), (.54, .078, .075, 0)], "dress")
            self.garment("purple_cape", [(.34, .151, .132, -.006),
                                         (.39, .165, .133, -.006),
                                         (.47, .155, .124, -.004),
                                         (.53, .113, .093, 0), (.565, .071, .068, 0)],
                          "cloth", .33)
            # Knot and two fabric loops, rather than an unattached sphere accessory.
            self.ell("scarf_knot", (0, .105, .525), (.022, .015, .023), "scarf")
            for side in (-1, 1):
                loop = self.ell(f"bow_loop_{side}", (side * .039, .104, .527),
                                (.035, .014, .020), "scarf")
                loop.rotation_euler.y = side * -.35
                self.mesh(f"scarf_end_{side}",
                          [(side * .012, .106, .516), (side * .031, .110, .516),
                           (side * .057, .127, .430), (side * .028, .130, .439)],
                          [(0, 1, 2, 3)], "scarf", .003)
            cap = self.ell("beret_crown", (.014, .006, head_z + .122),
                           (.111, .102, .048), "cloth")
            cap.rotation_euler.y = -.14
            self.ell("beret_band", (0, .010, head_z + .100), (.096, .091, .018), "cloth_dark")
            self.ell("beret_button", (.030, .012, head_z + .169), (.010, .010, .006), "cloth_dark")
        else:
            self.garment("red_sweater", [(.16, .131, .112, 0), (.20, .160, .129, 0),
                                        (.30, .178, .139, 0), (.38, .174, .137, 0),
                                        (.46, .153, .125, 0), (.51, .124, .105, 0),
                                        (.535, .101, .088, 0), (.557, .078, .077, 0)], "cloth")
            self.garment("ribbed_collar", [(.548, .089, .083, 0), (.578, .077, .077, 0)], "cloth_dark")
            self.garment("ribbed_hem", [(.165, .136, .117, 0), (.190, .155, .128, 0)], "cloth_dark")
            for i in range(28):
                angle = i * 2 * math.pi / 28
                self.line(f"collar_rib_{i}",
                          [(.090 * math.sin(angle), .084 * math.cos(angle), .552),
                           (.078 * math.sin(angle), .078 * math.cos(angle), .574)],
                          .0009, "cloth")
            self.ell("cap_band", (0, .012, head_z + .092), (.099, .089, .015), "cap_dark")
            self.ell("flat_cap_crown", (0, .009, head_z + .116), (.111, .098, .038), "cap")
            self.ell("cap_peak", (0, .101, head_z + .095), (.094, .068, .009), "cap")
            self.ell("cap_button", (0, .005, head_z + .155), (.009, .009, .006), "cap_dark")
            self.line("cap_seam", [(0, -.082, head_z + .112), (0, .005, head_z + .156),
                                   (0, .095, head_z + .112)], .0013, "cap_dark")
        # Head assembly can be posed as one unit without changing anatomy.
        pivot = bpy.data.objects.new(self.key + "_HeadPivot", None)
        self.collection.objects.link(pivot)
        pivot.parent = self.root
        pivot.location = (0, .015, head_z - .065)
        head_parts = ("head", "cheek", "nasal", "nose", "ear_", "eye_", "pupil", "upper_lid",
                      "lash", "brow", "smile", "whisker", "beret", "cap_", "flat_cap")
        for obj in self.objects:
            if obj.name[len(self.key) + 1:].startswith(head_parts):
                world = obj.matrix_basis.copy()
                obj.parent = pivot
                obj.matrix_basis = pivot.matrix_basis.inverted() @ world
        rig_character(self)
        return self

    def export(self, path):
        bpy.ops.object.select_all(action="DESELECT")
        self.root.select_set(True)
        for obj in self.collection.objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = self.root
        bpy.ops.export_scene.gltf(filepath=str(path.resolve()), export_format="GLB",
                                  use_selection=True, export_apply=True, export_yup=True,
                                  export_extras=True, export_animations=True)


def aim(obj, at):
    obj.rotation_euler = (Vector(at) - obj.location).to_track_quat("-Z", "Y").to_euler()


def studio():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 1400, 1000
    scene.render.resolution_percentage = 100
    scene.world.color = (.32, .32, .32)
    scene.view_settings.view_transform = "AgX"
    for name, at, energy, size in (("Key", (1.5, 2.4, 3.0), 160, 3.0),
                                    ("Fill", (-2, 1, 1.8), 100, 2.5),
                                    ("Rim", (0, -2, 2.2), 180, 2.0)):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size = energy, "DISK", size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = at
        aim(obj, (0, 0, .4))
    bpy.ops.mesh.primitive_plane_add(size=200)
    floor = bpy.context.object
    floor.name = "Studio_floor"
    floor.location.z = -.006
    floor.data.materials.append(material("Studio sage", (.18, .23, .21)))
    camera = bpy.data.cameras.new("ReviewCamera")
    obj = bpy.data.objects.new("ReviewCamera", camera)
    scene.collection.objects.link(obj)
    scene.camera = obj
    camera.type, camera.ortho_scale = "ORTHO", 1.72
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "art/source/generated/characters")
    parser.add_argument("--export-dir", type=Path, default=ROOT / "godot/assets/characters")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    expected = [args.output / "characters.blend", args.output / "manifest.json"]
    expected += [args.export_dir / f"{key.lower()}.glb" for key in ("Bernie", "Bianca")]
    if not args.overwrite and any(p.exists() for p in expected):
        raise FileExistsError("Character output exists; use --overwrite explicitly")
    args.output.mkdir(parents=True, exist_ok=True)
    args.export_dir.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    rig = json.loads((ROOT / "data/config/mouse_rig.json").read_text(encoding="utf-8"))
    config = json.loads((ROOT / "data/config/characters.json").read_text(encoding="utf-8"))
    characters = []
    for key, cfg in config["characters"].items():
        character = Character(key, cfg, rig).build()
        character.export(args.export_dir / f"{key.lower()}.glb")
        characters.append(character)
    # The exported characters each have their own unshifted origin and unit scale.
    characters[0].root.location.x = -.31
    characters[1].root.location.x = .31
    camera = studio()
    views = {"three_quarter": (1.45, 3.1, 1.40), "front": (0, 3.2, .55),
             "side": (3.2, .3, .70), "back": (.8, -3.2, 1.05),
             "paws_detail": (1.2, 3.2, 1.3), "faces_detail": (.7, 3.2, 1.05)}
    manifest = {"blender": bpy.app.version_string, "status": "skinned_attachment_rigs",
                "palette": "artistic approximation; not sampled from production cels",
                "characters": {}, "views": list(views),
                "limitations": ["exploration/climbing animations pending", "final cabin and clothing art review pending",
                                "runtime cape uses arm-following skin and capsule projection, not a full cloth solver"]}
    for c in characters:
        manifest["characters"][c.key] = {"role": c.config["role"], "mesh_objects": len(c.objects),
                                            "body_radii": c.config["body_radii"],
                                            "glb": f"{c.key.lower()}.glb", "bones": len(c.armature.data.bones),
                                            "hat_ear_intersections": int(c.root["hat_ear_intersections"])}
    for name, at in views.items():
        if name == "side":
            # Separate the silhouettes across the camera plane for inspection.
            characters[0].root.location = (0, -.31, 0)
            characters[1].root.location = (0, .31, 0)
        else:
            characters[0].root.location = (-.31, 0, 0)
            characters[1].root.location = (.31, 0, 0)
        camera.location = at
        camera.data.ortho_scale = 1.05 if name.endswith("detail") else 1.72
        target = (0, .025, .19) if name == "paws_detail" else (0, 0, .40)
        if name == "faces_detail":
            target = (0, .025, .66)
        aim(camera, target)
        if args.render:
            bpy.context.scene.render.filepath = str((args.output / f"{name}.png").resolve())
            bpy.ops.render.render(write_still=True)
    camera.location = views["three_quarter"]
    camera.data.ortho_scale = 1.72
    characters[0].root.location = (-.31, 0, 0)
    characters[1].root.location = (.31, 0, 0)
    aim(camera, (0, 0, .40))
    bpy.ops.wm.save_as_mainfile(filepath=str((args.output / "characters.blend").resolve()), compress=True)
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("CHARACTER_MODELS_GENERATED", json.dumps(manifest))


if __name__ == "__main__":
    main()
