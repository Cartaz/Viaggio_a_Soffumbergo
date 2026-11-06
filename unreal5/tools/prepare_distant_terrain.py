"""Prepare all source-backed distant tiles without starting a renderer."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from distant_terrain_mesh import adaptive_mesh

ROOT = Path(__file__).resolve().parents[1]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(); p.add_argument('--draft', type=Path, required=True)
    p.add_argument('--config', type=Path, default=ROOT/'parameters/distant_terrain_v1.json')
    args = p.parse_args()
    prep = json.loads((args.draft/'structure_preparation.json').read_text())
    imported = json.loads((args.draft/'import_report.json').read_text()); assert imported['all_imported']
    source = Path(prep['manifest']); m = json.loads(source.read_text()); cfg = json.loads(args.config.read_text())
    base = json.loads((ROOT/'terrain/world_tiles/manifest.json').read_text())
    signatures = {str(f.resolve()):sha(f) for f in [source,args.config,Path(__file__),ROOT/'tools/distant_terrain_mesh.py']}
    build = hashlib.sha256(json.dumps(signatures, sort_keys=True).encode()).hexdigest()[:12]
    folder = ROOT/'terrain/distant_terrain'/build
    if folder.exists(): raise RuntimeError('Preserve previous far terrain preparation')
    folder.mkdir(parents=True)
    report = {'build_id':build,'source_build_id':m['build_id'],'source_manifest':str(source),
        'config':cfg,'input_sha256':signatures,'started_unix':time.time(),'all_prepared':False,
        'native_imported':False,'rendered':False,'activated':False,'tiles':[]}
    manifest_path = folder/'manifest.json'
    zero_cm = (base['source_height_bounds_m'][0]-m['origin_ENH_m'][2])*100
    quantum_m = base['height_quantization_m']
    # Source hashes are checked before use; generated vertices never invent heights.
    for tile in m['tiles']:
        assert sha(tile['heightmap']) == tile['height_sha256'] and sha(tile['holes']) == tile['holes_sha256']
        n=tile['samples']; h=np.fromfile(tile['heightmap'],'<u2').reshape(n,n)
        holes=np.fromfile(tile['holes'],'u1').reshape(n,n)
        vertices,faces,sample_xy,leaves,error=adaptive_mesh(h,holes,cfg['candidate_sample_strides'],tile['xy_scale_cm'],quantum_m*100,zero_cm,cfg['max_native_vertex_error_m'])
        if len(faces):
            cross=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
            if not np.all(cross[:,2]>0): raise RuntimeError('Degenerate or reversed XY face')
        # Binary preparation avoids a large JSON intermediate; import can read
        # arrays directly and author native meshes without changing source data.
        path=folder/(tile['id']+'.npz')
        np.savez_compressed(path,vertices_cm=vertices,triangles=faces,source_sample_xy=sample_xy,leaf_cells=leaves)
        row={'id':tile['id'],'source_map':tile['map'],'bounds_xy_cm':tile['bounds_xy_cm'],
            'location_cm':[*tile['location_cm'][:2],0], 'heightmap':tile['heightmap'],'holes':tile['holes'],
            'height_sha256':tile['height_sha256'],'holes_sha256':tile['holes_sha256'],
            'asset':'/Game/World/Distant/D_'+build+'/Meshes/SM_'+tile['id'],
            'source':str(path),'sha256':sha(path),'vertices':len(vertices),'triangles':len(faces),
            'adaptive_strides':cfg['candidate_sample_strides'],'selected_error':error,
            'collision_enabled':False,'cast_shadow':False}
        report['tiles'].append(row); manifest_path.write_text(json.dumps(report,indent=2))
        print('FAR_TILE '+tile['id']+' triangles='+str(len(faces))+' max_error_m='+str(round(error['max_error_m'],4)),flush=True)
    report.update(all_prepared=len(report['tiles'])==len(m['tiles']),ended_unix=time.time(),
        total_vertices=sum(t['vertices'] for t in report['tiles']),total_triangles=sum(t['triangles'] for t in report['tiles']),
        maximum_native_vertex_error_m=max(t['selected_error']['max_error_m'] for t in report['tiles']),
        limits=['Approximation error checked at native raster vertices; not a continuous triangle-intersection bound.',
                'Native boundary vertices retained where adjacent cells survive; no crack certification until independent audit and native execution.',
                'Cells touching source holes omitted conservatively, potentially expanding missing ground by a coarse cell.',
                'No scenery is added outside the available LiDAR coverage.',
                'Not yet imported, connected to streaming, or visually/performance accepted.'])
    manifest_path.write_text(json.dumps(report,indent=2)); print(json.dumps({k:report[k] for k in ['build_id','all_prepared','total_vertices','total_triangles','maximum_native_vertex_error_m']},indent=2))


if __name__ == '__main__': main()
