"""Create a checked native Blender overview of the whole local DTM corridor."""
import argparse
import json
from pathlib import Path
import sys
import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from coffa.terrain import grid_triangles
from register_dtm import sha256_file
from build_valle import mesh_object


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=ROOT/'build/circuit/manifest.json')
    parser.add_argument('--output',type=Path,default=ROOT/'build/circuit_validation/circuit_overview.blend')
    parser.add_argument('--overwrite',action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if not args.output.resolve().is_relative_to(ROOT/'build'):
        raise ValueError('Terrain derivatives must remain under build/')
    if args.output.exists() and not args.overwrite:
        raise FileExistsError(args.output)
    doc = json.loads(args.data.read_text(encoding='utf-8'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection = bpy.data.collections.new('Circuit_DTM_Overview_8m_LOCAL_ONLY')
    bpy.context.scene.collection.children.link(collection)
    triangles = 0
    for entry in doc['sectors']:
        s = entry['overview']
        side = s['side']
        x,z = s['offset_xz_m']
        vertices = [(x+c*8,-(z+r*8),s['heights_m'][r*side+c] or 0)
                    for r in range(side) for c in range(side)]
        faces = [tuple(reversed(face)) for face in grid_triangles(side)
                 if all(s['heights_m'][i] is not None for i in face)]
        obj = mesh_object('Terrain_'+s['id'],vertices,faces,collection)
        if any(p.normal.z <= 0 for p in obj.data.polygons):
            raise ValueError('Downward terrain face')
        obj['origin_ENH_m'] = doc['origin_ENH_m']
        obj['source_chunk_sha256'] = entry['sha256']
        obj['source_chunk_path'] = entry['path']
        obj['status'] = '8m_visual_overview_not_2m_collision_or_asphalt'
        triangles += len(faces)
    for b in doc['valle_content']['buildings']:
        ring = b['ring_xz_m']
        n = len(ring)
        vertices = [(p[0],-p[1],y) for y in [b['base_y_m'],b['roof_y_m']] for p in ring]
        faces = [tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        obj = mesh_object('OSM_'+b['id'].replace('/','_'),vertices,faces,collection)
        obj['source_url'] = b['source_url']
        obj['height_status'] = b['height_status']
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1
    args.output.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output.resolve()))
    report = {'blender_version':bpy.app.version_string,'terrain_sectors':len(doc['sectors']),
              'overview_terrain_triangles':triangles,'building_count':len(doc['valle_content']['buildings']),
              'source_manifest_sha256':sha256_file(args.data),'axes':'Blender +X east, +Y north, +Z up',
              'normals_and_mesh_validation_passed':True,'scope':'coarse overview, not streamed 2m physics or artistic approval'}
    (args.output.parent/'blender_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
