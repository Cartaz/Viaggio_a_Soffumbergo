"""Create and validate the local georeferenced Valle blockout in real Blender.

blender --background --factory-startup --python tools/blender/build_valle.py
Original raster and derived mesh redistribution remain pending rights review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from coffa.terrain import grid_triangles


def mesh_object(name, vertices, faces, collection):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    if mesh.validate():
        raise ValueError('Blender repaired invalid geometry: ' + name)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT/'build/valle/valle_scene.json')
    parser.add_argument('--output', type=Path, default=ROOT/'build/valle_validation/valle.blend')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if not args.output.resolve().is_relative_to(ROOT/'build'):
        raise ValueError('Terrain derivatives must remain under ignored build/')
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(args.output)
    doc = json.loads(args.data.read_text(encoding='utf-8'))
    collection = bpy.data.collections.new('Valle_3D_01_LOCAL_ONLY')
    bpy.context.scene.collection.children.link(collection)
    # Keep default startup objects in a separate collection; only our collection is exported.
    failures = []
    terrain_triangles = 0
    for sector in doc['sectors']:
        side = sector['side']
        x, z = sector['offset_xz_m']
        vertices = [(x+c*2, -(z+r*2), sector['heights_m'][r*side+c])
                    for r in range(side) for c in range(side)]
        # Godot clockwise -> Blender counter-clockwise; axis rotation has determinant +1.
        faces = [tuple(reversed(f)) for f in grid_triangles(side)]
        obj = mesh_object('Terrain_'+sector['id'], vertices, faces, collection)
        if any(p.normal.z <= 0 for p in obj.data.polygons):
            failures.append(obj.name + ': downward terrain face')
        terrain_triangles += len(faces)
        obj['origin_ENH_m'] = doc['origin_ENH_m']
        obj['horizontal_crs'] = doc['horizontal_crs']
        obj['vertical_reference'] = doc['vertical_reference']
    for building in doc['buildings']:
        ring = building['ring_xz_m']
        n = len(ring)
        vertices = [(p[0], -p[1], y) for y in (building['base_y_m'], building['roof_y_m']) for p in ring]
        faces = [tuple(range(n, 2*n))]
        faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
        obj = mesh_object('OSM_'+building['id'].replace('/', '_'), vertices, faces, collection)
        obj['height_status'] = building['height_status']
        obj['source_url'] = building['source_url']
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    report = {'blender_version': bpy.app.version_string, 'terrain_sectors': len(doc['sectors']),
              'terrain_triangles': terrain_triangles, 'building_count': len(doc['buildings']),
              'source_scene_sha256': hashlib.sha256(args.data.read_bytes()).hexdigest(),
              'axes': 'Blender +X east, +Y north, +Z up', 'failures': failures,
              'scope': 'mesh validation, terrain normals and native project save; no artistic approval'}
    (args.output.parent/'blender_report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))
    if failures:
        raise RuntimeError('Blender geometry gate failed')


if __name__ == '__main__':
    main()
