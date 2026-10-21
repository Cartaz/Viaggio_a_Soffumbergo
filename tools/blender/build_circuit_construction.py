"""Save the entire local construction surface and coarse terrain in native Blender."""
import json
from pathlib import Path
import sys
import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_valle import mesh_object
from coffa.terrain import grid_triangles
from register_dtm import sha256_file


def main():
    folder = ROOT/'build/circuit'
    doc = json.loads((folder/'construction_manifest.json').read_bytes())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    roads = bpy.data.collections.new('Provisional_Road_Not_Surveyed')
    terrain = bpy.data.collections.new('Derived_Earthworks_Overview_8m')
    bpy.context.scene.collection.children.link(roads)
    bpy.context.scene.collection.children.link(terrain)
    count = 0
    for item in doc['engineering_construction']['road_sectors']:
        path = folder/item['path']
        if sha256_file(path) != item['sha256']:
            raise ValueError('Changed road chunk')
        road = json.loads(path.read_bytes())
        ox, oz = map(float, item['id'].split('_'))
        # Blender mesh coordinates are float32: keep road vertices tile-local,
        # subtracting in Python doubles before creating the native mesh.
        vertices = [(x-ox, -(z-oz), y) for x, y, z in road['vertices_m']]
        obj = mesh_object('Road_'+item['id'], vertices, [tuple(reversed(t)) for t in road['triangles']], roads)
        obj.location = (ox, -oz, 0)
        if any(p.normal.z <= 0 for p in obj.data.polygons):
            raise ValueError('Folded road face')
        obj['status'] = road['status']
        obj['origin_ENH_m'] = doc['origin_ENH_m']
        count += len(obj.data.polygons)
    for entry in doc['sectors']:
        s = entry['overview']
        x, z = s['offset_xz_m']
        vertices = [(x+c*8, -(z+r*8), s['heights_m'][r*17+c] or 0) for r in range(17) for c in range(17)]
        faces = [tuple(reversed(f)) for f in grid_triangles(17) if all(s['heights_m'][i] is not None for i in f)]
        mesh_object('Terrain_'+s['id'], vertices, faces, terrain)
    bpy.context.scene.unit_settings.system = 'METRIC'
    output = ROOT/'build/construction_validation'
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'circuit_construction.blend'))
    report = {'passed':True, 'blender_version':bpy.app.version_string, 'road_sectors':len(roads.objects),
              'road_triangles':count, 'terrain_overview_sectors':len(terrain.objects),
              'manifest_sha256':sha256_file(folder/'construction_manifest.json'),
              'scope':'native mesh and normals, not artistic approval or driven lap'}
    (output/'blender_report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
