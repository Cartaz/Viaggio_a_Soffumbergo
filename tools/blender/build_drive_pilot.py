"""Validate the local engineering road and seven modified 2m terrain chunks in Blender."""
import hashlib
import json
from pathlib import Path
import sys
import bpy

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from coffa.terrain import grid_triangles
from build_valle import mesh_object


def main():
    folder=ROOT/'build/circuit'
    output=ROOT/'build/drive_validation'
    output.mkdir(parents=True,exist_ok=True)
    road=json.loads((folder/'pilot_road.json').read_text())
    manifest=json.loads((folder/'pilot_manifest.json').read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection=bpy.data.collections.new('ENGINEERING_TRIAL_NOT_SURVEYED_LOCAL_ONLY')
    bpy.context.scene.collection.children.link(collection)
    vertices=[(p[0],-p[2],p[1]) for p in road['vertices_m']]
    obj=mesh_object('Trial_road',vertices,[tuple(reversed(f)) for f in road['triangles']],collection)
    if any(p.normal.z<=0 for p in obj.data.polygons):
        raise ValueError('Road normal points downward')
    obj['width_status']=road['width_status']
    obj['vertical_status']=road['vertical_status']
    chunks=0
    for e in manifest['sectors']:
        if '/drive_' not in e['path']:
            continue
        b=(folder/e['path']).read_bytes()
        if hashlib.sha256(b).hexdigest()!=e['sha256']:
            raise ValueError('Chunk checksum mismatch')
        d=json.loads(b); ox,oz=d['offset_xz_m']
        vertices=[(ox+c*2,-(oz+r*2),d['heights_m'][r*65+c]) for r in range(65) for c in range(65)]
        mesh_object('Graded_'+d['id'],vertices,[tuple(reversed(f)) for f in grid_triangles(65)],collection)
        chunks+=1
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'engineering_trial.blend'))
    report={'blender':bpy.app.version_string,'road_triangles':len(road['triangles']),
            'modified_2m_terrain_chunks':chunks,'mesh_validation_passed':True,
            'pilot_road_sha256':hashlib.sha256((folder/'pilot_road.json').read_bytes()).hexdigest(),
            'scope':'geometry only; no approval of real road widths, grading or junctions'}
    (output/'blender_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
