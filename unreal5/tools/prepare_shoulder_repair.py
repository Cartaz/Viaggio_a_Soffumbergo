"""Replace earth overlays only; preserve proven asphalt, structures and R16."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from native_shoulder_overlay import overlay
from prepare_reentry_checks import NativeGround
from road_surface import RoadSurface

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--parent-draft',type=Path,required=True);args=p.parse_args()
    parent=args.parent_draft.resolve();imported=json.loads((parent/'import_report.json').read_text())
    if not imported['all_imported']:raise RuntimeError('Native parent import is required')
    manifest_path=Path(imported['manifest']);original=json.loads(manifest_path.read_text())
    inputs=[manifest_path,parent/'circuit_driving_world.json',parent/'circuit_itinerary.json',Path(__file__),
        ROOT/'tools/native_shoulder_overlay.py',ROOT/'tools/road_surface.py',ROOT/'tools/prepare_reentry_checks.py']
    signatures={str(path):sha(path) for path in inputs}
    build=hashlib.sha256(json.dumps(signatures,sort_keys=True).encode()).hexdigest()[:12]
    folder=ROOT/'terrain/road_shoulders'/build;draft=ROOT/'results/road_drafts'/build
    if folder.exists() or draft.exists():raise RuntimeError('Preserve earlier repair draft')
    folder.mkdir(parents=True);draft.mkdir(parents=True)
    ground=NativeGround(original);road=RoadSurface(original);records=[];diagnostics=[]
    for old in original['meshes']:
        if old['kind']!='shoulder':continue
        tile=next(t for t in original['tiles'] if t['id']==old['tile'])
        vertices,triangles,diagnostic=overlay(tile,old,ground,road)
        location=np.asarray(old['location_cm']);local=np.round(vertices*100-location,5)
        cross=np.cross(local[triangles[:,1]]-local[triangles[:,0]],local[triangles[:,2]]-local[triangles[:,0]])
        keep=(cross*cross).sum(axis=1)>=1.e-8
        diagnostic['native_creator_precision_faces_removed']=int(np.count_nonzero(~keep))
        triangles=triangles[keep]
        data={'vertices_cm':local.tolist(),'triangles':triangles.tolist()}
        path=folder/(old['id']+'.json');path.write_text(json.dumps(data,separators=(',',':')))
        records.append({**old,'source':str(path),'sha256':sha(path),
            'asset':'/Game/World/Driving/H_'+build+'/Meshes/'+old['id'],
            'vertices':len(vertices),'triangles':len(triangles),'native_grid_overlay':True})
        diagnostics.append({'tile':old['tile'],**diagnostic})
        print('NATIVE_SHOULDER '+old['tile']+' '+str(len(triangles)),flush=True)
    m=copy.deepcopy(original);m['build_id']=build
    replacements={r['id']:r for r in records}
    m['meshes']=[replacements.get(r['id'],r) for r in original['meshes']]
    changed={r['tile'] for r in records}
    for tile in m['tiles']:
        if tile['id'] in changed:
            tile['shoulder_parent_map']=tile['map']
            tile['map']='/Game/World/Driving/H_'+build+'/Terrain/'+tile['id']
    m['shoulder_repair']={'parent_build_id':original['build_id'],'parent_manifest':str(manifest_path),
        'parent_draft':str(parent),'input_sha256':signatures,'records':records,'diagnostics':diagnostics,
        'asphalt_native_height_holes_and_structures_changed':False,
        'native_visibility_policy':'Overlay omitted only over native quads touching a masked sample; no ground is invented in bridge holes or absent source cells. Existing asphalt and bridge slabs remain unchanged.',
        'scope':'Existing earth overlay footprint resampled on native grid; narrow asphalt seam blend only. Not final anthropic coverage or slope-support approval.'}
    m['report'].update(build_id=build,native_imported=False,full_lap_driven=False)
    manifest=folder/'manifest.json';manifest.write_text(json.dumps(m,indent=2))
    world=json.loads((parent/'circuit_driving_world.json').read_text());world['build_id']=build
    maps={t['id']:t['map'] for t in m['tiles']}
    for tile in world['tiles']:tile['map']=maps[tile['id']]
    (draft/'circuit_driving_world.json').write_text(json.dumps(world))
    itinerary=json.loads((parent/'circuit_itinerary.json').read_text());itinerary['build_id']=build
    (draft/'circuit_itinerary.json').write_text(json.dumps(itinerary))
    prepared={'build_id':build,'parent_build_id':original['build_id'],'manifest':str(manifest),'draft':str(draft),
        'change_kind':'native_grid_shoulder_overlay','replaced_shoulder_meshes':len(records),
        'retained_structure_solids':len(m['roadside_structures']['collision_probes']),'activated':False}
    (draft/'structure_preparation.json').write_text(json.dumps(prepared,indent=2))
    print(json.dumps(prepared,indent=2))


if __name__=='__main__':main()
