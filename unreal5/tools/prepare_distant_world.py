"""Stage verified far geometry and version a complete, isolated driving world."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct

import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--parent-draft',type=Path,required=True)
    p.add_argument('--far-manifest',type=Path,required=True);p.add_argument('--far-audit',type=Path,required=True)
    args=p.parse_args(); parent=args.parent_draft.resolve(); imported=json.loads((parent/'import_report.json').read_text())
    assert imported['all_imported']; original_path=Path(imported['manifest']);original=json.loads(original_path.read_text())
    far=json.loads(args.far_manifest.read_text());audit=json.loads(args.far_audit.read_text())
    assert far['all_prepared'] and audit['passed'] and audit['build_id']==far['build_id'] and len(audit['tiles'])==len(far['tiles'])==113
    assert audit['source_manifest_sha256']==sha(args.far_manifest)
    inputs=[original_path,parent/'circuit_driving_world.json',parent/'circuit_itinerary.json',args.far_manifest,args.far_audit,
        Path(__file__),ROOT/'tools/import_distant_world.py',ROOT/'Unreal/Source/SoffumbergoLab/CircuitTerrainWorld.cpp',
        ROOT/'Unreal/Source/SoffumbergoLab/CircuitTerrainWorld.h',ROOT/'Unreal/Source/SoffumbergoTerrainEditor/DistantTerrainMesh.cpp',
        ROOT/'Unreal/Source/SoffumbergoTerrainEditor/LidarTerrainLibrary.h',ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoLab.dll',
        ROOT/'Unreal/Binaries/Win64/UnrealEditor-SoffumbergoTerrainEditor.dll']
    signatures={str(p.resolve()):sha(p) for p in inputs}
    build=hashlib.sha256(json.dumps(signatures,sort_keys=True).encode()).hexdigest()[:12]
    folder=ROOT/'terrain/distant_world'/build;draft=ROOT/'results/road_drafts'/build
    if folder.exists() or draft.exists(): raise RuntimeError('Preserve previous native far candidate')
    folder.mkdir(parents=True);draft.mkdir(parents=True);m=copy.deepcopy(original);m['build_id']=build
    by_id={t['id']:t for t in far['tiles']};records=[]
    for tile in m['tiles']:
        f=by_id[tile['id']]
        assert f['height_sha256']==tile['height_sha256'] and f['holes_sha256']==tile['holes_sha256']
        assert sha(tile['heightmap'])==tile['height_sha256'] and sha(tile['holes'])==tile['holes_sha256']
        assert sha(f['source'])==f['sha256']
        with np.load(f['source']) as data: v=data['vertices_cm'].astype('<f8');faces=data['triangles'].astype('<u4')
        binary=folder/(tile['id']+'.sfd')
        with binary.open('xb') as out:
            out.write(struct.pack('<4sIII',b'SFD1',1,len(v),len(faces)));out.write(v.tobytes());out.write(faces.tobytes())
        tile['distant_map']='/Game/World/Distant/R_'+build+'/Levels/D_'+tile['id']
        records.append({'id':tile['id'],'map':tile['distant_map'],
            'asset':'/Game/World/Distant/R_'+build+'/Meshes/SM_'+tile['id'],
            'source_geometry':f['source'],'source_geometry_sha256':f['sha256'],
            'binary':str(binary),'binary_sha256':sha(binary),'vertices':len(v),'triangles':len(faces),
            'location_cm':f['location_cm'],'collision_enabled':False,'cast_shadow':False})
    m['distant_terrain']={'parent_build_id':original['build_id'],'parent_manifest':str(original_path),'parent_draft':str(parent),
        'geometry_manifest':str(args.far_manifest.resolve()),'geometry_audit':str(args.far_audit.resolve()),
        'input_sha256':signatures,'records':records,'material_asset':'/Game/World/Distant/R_'+build+'/Materials/M_DistantLidar',
        'near_geometry_physics_and_pcg_changed':False,'native_imported':False,'visual_quality_approved':False,
        'scope':'Complete source-backed far terrain. Lightweight levels stay loaded, visible only where the corresponding detailed Landscape is not visible. No collision, no cast shadows, no external heights.'}
    m['report'].update(build_id=build,native_imported=False,full_lap_driven=False)
    manifest=folder/'manifest.json';manifest.write_text(json.dumps(m,indent=2))
    world=json.loads((parent/'circuit_driving_world.json').read_text());world['build_id']=build
    maps={t['id']:t['distant_map'] for t in m['tiles']}
    for tile in world['tiles']: tile['distant_map']=maps[tile['id']]
    (draft/'circuit_driving_world.json').write_text(json.dumps(world))
    route=json.loads((parent/'circuit_itinerary.json').read_text());route['build_id']=build
    (draft/'circuit_itinerary.json').write_text(json.dumps(route))
    assert m['meshes']==original['meshes']
    for a,b in zip(m['tiles'],original['tiles']): assert {k:v for k,v in a.items() if k!='distant_map'}==b
    report={'build_id':build,'parent_build_id':original['build_id'],'manifest':str(manifest),'draft':str(draft),
        'change_kind':'whole_world_native_distant_terrain','distant_tiles':len(records),'near_geometry_changed':False,'activated':False}
    (draft/'structure_preparation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__': main()
