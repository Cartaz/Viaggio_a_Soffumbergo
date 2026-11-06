"""Retain independently accepted far tiles and refine rejected local cells."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from distant_terrain_mesh import adaptive_mesh

ROOT=Path(__file__).resolve().parents[1]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--audit',type=Path,required=True)
    args=p.parse_args(); old=json.loads(args.manifest.read_text());audit=json.loads(args.audit.read_text())
    assert old['all_prepared'] and audit['build_id']==old['build_id'] and len(audit['tiles'])==len(old['tiles']) and not audit.get('error')
    failed={t['id'] for t in audit['tiles'] if not t['passed']}; assert failed
    inputs={str(p.resolve()):sha(p) for p in [args.manifest,args.audit,Path(__file__),ROOT/'tools/distant_terrain_mesh.py']}
    build=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:12]
    folder=ROOT/'terrain/distant_terrain'/build
    if folder.exists(): raise RuntimeError('Preserve previous refinement')
    folder.mkdir(parents=True)
    m=copy.deepcopy(old);m.update(build_id=build,parent_far_build_id=old['build_id'],parent_far_manifest=str(args.manifest.resolve()),
        input_sha256=inputs,all_prepared=False,started_unix=time.time(),tiles=[],native_imported=False,rendered=False)
    base=json.loads((ROOT/'terrain/world_tiles/manifest.json').read_text()); source=json.loads(Path(old['source_manifest']).read_text())
    by_id={t['id']:t for t in source['tiles']};quantum=base['height_quantization_m'];zero=(base['source_height_bounds_m'][0]-source['origin_ENH_m'][2])*100
    manifest=folder/'manifest.json'
    for previous in old['tiles']:
        tile=copy.deepcopy(previous); assert sha(tile['source'])==tile['sha256']
        tile['asset']='/Game/World/Distant/D_'+build+'/Meshes/SM_'+tile['id']
        tile['inherited_geometry_bytes']=tile['id'] not in failed
        if tile['id'] in failed:
            original=by_id[tile['id']]; n=original['samples']
            assert sha(original['heightmap'])==tile['height_sha256'] and sha(original['holes'])==tile['holes_sha256']
            height=np.fromfile(original['heightmap'],'<u2').reshape(n,n); holes=np.fromfile(original['holes'],'u1').reshape(n,n)
            v,f,xy,leaves,error=adaptive_mesh(height,holes,m['config']['candidate_sample_strides'],original['xy_scale_cm'],quantum*100,zero,m['config']['max_native_vertex_error_m'])
            path=folder/(tile['id']+'.npz');np.savez_compressed(path,vertices_cm=v,triangles=f,source_sample_xy=xy,leaf_cells=leaves)
            tile.update(source=str(path),sha256=sha(path),vertices=len(v),triangles=len(f),selected_error=error)
            print('FAR_REFINED '+tile['id']+' passes='+str(error['interior_refinement_passes']),flush=True)
        m['tiles'].append(tile);manifest.write_text(json.dumps(m,indent=2))
    m.update(all_prepared=True,ended_unix=time.time(),refined_tiles=sorted(failed),
        total_vertices=sum(t['vertices'] for t in m['tiles']),total_triangles=sum(t['triangles'] for t in m['tiles']),
        maximum_native_vertex_error_m=max(t['selected_error']['max_error_m'] for t in m['tiles']),
        limits=['Native vertices and finite triangle probes checked, not a continuous maximum-error certificate.',
            'NoData domain follows the native four-corner validity rule; no extrapolation.',
            'Native import, streaming, visual quality and performance remain unverified.'])
    manifest.write_text(json.dumps(m,indent=2));print(json.dumps({'manifest':str(manifest),'refined_tiles':sorted(failed),'total_triangles':m['total_triangles']},indent=2))


if __name__=='__main__': main()
