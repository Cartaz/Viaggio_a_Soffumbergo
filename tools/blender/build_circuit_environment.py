"""Add reproducible coded placeholders to the checked private construction scene.

The base must already contain the approved Yaris, pirate rig and both mice.
Never publishes the native project, which includes private assets.
"""
import hashlib
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix
import math

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    base = ROOT/'build/construction_validation/circuit_construction.blend'
    evidence = json.loads((base.parent/'blender_report.json').read_bytes())
    catalog_path = ROOT/'data/geography/circuit_placeholders.json'
    catalog = json.loads(catalog_path.read_bytes())
    if not evidence['passed'] or evidence['manifest_sha256'] != catalog['construction_manifest_sha256']:
        raise ValueError('Checked construction scene for current terrain required')
    bpy.ops.wm.open_mainfile(filepath=str(base))
    names = [o.name for o in bpy.data.objects]
    for expected in ['YarisGameVisual', 'PirateRig', 'BernieDriver', 'BiancaLookout']:
        if not any(expected in n for n in names):
            raise ValueError('Approved assembly missing: '+expected)
    native = bpy.data.collections.new('Coded_Environment_Visual_Only')
    bpy.context.scene.collection.children.link(native)
    mats, meshes = {}, {}
    def mesh(kind, color):
        key = kind+color
        if key in meshes:
            return meshes[key]
        if kind == 'box':
            bpy.ops.mesh.primitive_cube_add(size=1)
        elif kind == 'sphere':
            bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, radius=.5)
        else:
            bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=.5, radius2=0 if kind == 'cone' else .5, depth=1)
        template = bpy.context.object
        value = template.data
        if color not in mats:
            material = bpy.data.materials.new('Placeholder_'+color)
            material.diffuse_color = tuple(int(color[i:i+2], 16)/255 for i in (0, 2, 4))+(1,)
            material.roughness = .95
            mats[color] = material
        value.materials.append(mats[color])
        meshes[key] = value
        bpy.data.objects.remove(template, do_unlink=True)
        return value
    # Godot X,Y,Z -> Blender X,-Z,Y. Keep local origins before float conversion.
    axis = Matrix(((1,0,0,0), (0,0,-1,0), (0,1,0,0), (0,0,0,1)))
    count, primitives = 0, 0
    for item in catalog['objects']:
        if item['runtime_status'] != 'visible_blockout':
            continue
        root = bpy.data.objects.new(item['code'], None)
        native.objects.link(root)
        x, y, z = item['position_m']
        root.location = (x, -z, y)
        root['code'] = item['code']
        root['description'] = item['description']
        root['category'] = item['category']
        root['position_status'] = item['position_status']
        root['dimensions_status'] = item['dimensions_status']
        root['recipe_json'] = json.dumps(item, ensure_ascii=False)
        root['collision_enabled'] = False
        yaw = Matrix.Rotation(math.radians(item['yaw_deg']), 4, 'Y')
        for index, p in enumerate(item['primitives']):
            obj = bpy.data.objects.new(item['code']+'_'+str(index), mesh(p['kind'], p['color']))
            native.objects.link(obj)
            obj.parent = root
            local = Matrix.Translation(p['center_m']) @ Matrix.Diagonal(p['size_m']+[1])
            obj.matrix_basis = axis @ yaw @ local
            primitives += 1
        count += 1
    output = ROOT/'build/environment_validation'
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'circuit_environment.blend'))
    report = {'passed':True, 'blender_version':bpy.app.version_string,
              'catalog_sha256':sha(catalog_path), 'catalog_build_id':catalog['build_id'],
              'objects_checked':count, 'primitives_checked':primitives,
              'approved_assembly_present':True,
              'approved_vehicle_snapshot_sha256':evidence['approved_vehicle_snapshot_sha256'],
              'construction_manifest_sha256':evidence['manifest_sha256'],
              'base_native_sha256':sha(base),
              'native_scene_sha256':sha(output/'circuit_environment.blend'),
              'scope':'coded native visual blockout with private final assembly; not metric or artistic approval'}
    (output/'blender_report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
