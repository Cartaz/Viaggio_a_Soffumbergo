"""Independently inspect persisted far meshes, domain, seams and R16 probes."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(); p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--attempt',default='v1'); args=p.parse_args()
    if not args.attempt.replace('_','').isalnum(): raise ValueError('Unsafe audit attempt')
    m=json.loads(args.manifest.read_text()); assert m['all_prepared']
    out=args.manifest.parent/('geometry_audit_'+args.attempt+'.json')
    if out.exists(): raise RuntimeError('Preserve previous audit')
    source=json.loads(Path(m['source_manifest']).read_text()); by_id={t['id']:t for t in source['tiles']}
    base=json.loads((ROOT/'terrain/world_tiles/manifest.json').read_text())
    quantum=base['height_quantization_m']; zero=base['source_height_bounds_m'][0]-source['origin_ENH_m'][2]
    rows=[]; seams={}; shared=0
    report={'build_id':m['build_id'],'started_unix':time.time(),'passed':False,'tiles':rows,
            'native_imported':False,'rendered':False,'source_manifest_sha256':sha(args.manifest)}
    try:
        for tile in m['tiles']:
            original=by_id[tile['id']]; n=original['samples']; spacing=original['xy_scale_cm']
            assert sha(tile['source'])==tile['sha256']
            assert sha(original['heightmap'])==tile['height_sha256']
            assert sha(original['holes'])==tile['holes_sha256']
            h=np.fromfile(original['heightmap'],'<u2').reshape(n,n)
            holes=np.fromfile(original['holes'],'u1').reshape(n,n)
            with np.load(tile['source']) as mesh:
                v=mesh['vertices_cm']; f=mesh['triangles']; xy=mesh['source_sample_xy']; leaves=mesh['leaf_cells']
            assert v.shape==(tile['vertices'],3) and f.shape==(tile['triangles'],3)
            assert len(np.unique(xy,axis=0))==len(v)
            assert np.all((xy>=0)&(xy<n)) and np.array_equal(v[:,:2],xy*spacing)
            expected=h[xy[:,1],xy[:,0]].astype(float)*quantum*100+zero*100
            assert np.max(np.abs(v[:,2]-expected),initial=0)<1e-6
            assert np.all((f>=0)&(f<len(v)))
            triangles=xy[f]; a=triangles[:,1]-triangles[:,0]; b=triangles[:,2]-triangles[:,0]
            twice_area=a[:,0]*b[:,1]-a[:,1]*b[:,0]
            assert np.all(twice_area>0)
            occupancy=np.zeros((n-1,n-1),bool)
            count=0
            for x,y,s,start,length in leaves:
                assert start==count and 0<=x<x+s<n and 0<=y<y+s<n
                assert not np.any(occupancy[y:y+s,x:x+s])
                assert not np.any(holes[y:y+s+1,x:x+s+1])
                group=triangles[start:start+length]
                assert np.all((group[:,:,0]>=x)&(group[:,:,0]<=x+s)&(group[:,:,1]>=y)&(group[:,:,1]<=y+s))
                assert abs(twice_area[start:start+length].sum()-2*s*s)<1e-8
                occupancy[y:y+s,x:x+s]=True; count+=length
            assert count==len(f)
            valid=(holes[:-1,:-1]==0)&(holes[1:,:-1]==0)&(holes[:-1,1:]==0)&(holes[1:,1:]==0)
            assert np.array_equal(occupancy,valid)
            edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
            unique,counts=np.unique(edges,axis=0,return_counts=True)
            assert np.all(counts<=2)
            boundary=xy[unique[counts==1]]
            if len(boundary):
                d=boundary[:,1]-boundary[:,0]
                horizontal=d[:,1]==0; vertical=d[:,0]==0
                assert np.all(horizontal ^ vertical)
                mid=boundary.mean(1)
                for selection,is_horizontal in [(horizontal,True),(vertical,False)]:
                    pts=mid[selection]; ix=np.floor(pts[:,0]).astype(int); iy=np.floor(pts[:,1]).astype(int)
                    leftx=ix; lefty=iy-1 if is_horizontal else iy
                    if not is_horizontal: leftx=ix-1
                    rightx=ix; righty=iy
                    def present(x,y):
                        inside=(x>=0)&(x<n-1)&(y>=0)&(y<n-1)
                        result=np.zeros(len(x),bool); result[inside]=occupancy[y[inside],x[inside]]; return result
                    assert np.all(present(leftx,lefty) ^ present(rightx,righty)), 'Crack, T junction or boundary outside source domain'
            for axis,constant,adjacent in [(1,0,valid[0,:]),(1,n-1,valid[-1,:]),(0,0,valid[:,0]),(0,n-1,valid[:,-1])]:
                desired=np.zeros(n,bool); desired[:-1]|=adjacent; desired[1:]|=adjacent
                actual=np.zeros(n,bool); actual[xy[xy[:,axis]==constant,1-axis]]=True
                assert np.array_equal(actual,desired), 'Native boundary samples missing'
            edge_ids=np.flatnonzero(np.any((xy==0)|(xy==n-1),axis=1))
            for i in edge_ids:
                key=(int(original['location_cm'][0]+v[i,0]),int(original['location_cm'][1]+v[i,1]))
                z=float(v[i,2])
                if key in seams:
                    assert abs(z-seams[key])<1e-6, 'Neighbor height mismatch'
                    shared+=1
                else: seams[key]=z
            # New samples not used by the simplifier: triangle centroids and
            # three edge midpoints, evaluated against original TL/BR triangles.
            max_probe=0.; sumsq=0.; probes=0
            for weights in [[1/3,1/3,1/3],[.5,.5,0],[.5,0,.5],[0,.5,.5]]:
                weights=np.array(weights); pxy=triangles.transpose(0,2,1)@weights
                ix=np.minimum(np.floor(pxy[:,0]).astype(int),n-2); iy=np.minimum(np.floor(pxy[:,1]).astype(int),n-2)
                fx=pxy[:,0]-ix; fy=pxy[:,1]-iy
                aa=h[iy,ix].astype(float); bb=h[iy,ix+1].astype(float)
                cc=h[iy+1,ix].astype(float); dd=h[iy+1,ix+1].astype(float)
                z=np.where(fx>=fy,aa+(bb-aa)*fx+(dd-bb)*fy,aa+(dd-cc)*fx+(cc-aa)*fy)
                expected=(z*quantum+zero)*100; actual=v[f,2]@weights
                error=(actual-expected)/100
                max_probe=max(max_probe,float(np.max(np.abs(error),initial=0))); sumsq+=float(error@error); probes+=len(error)
            probe_pass=max_probe <= m['config']['max_native_vertex_error_m']+1e-8
            rows.append({'id':tile['id'],'passed':probe_pass,'vertices':len(v),'triangles':len(f),
                'native_domain_cells':int(valid.sum()),'boundary_edges':len(boundary),
                'source_vertices_exact':True,'hole_domain_exact_under_four_corner_rule':True,
                'no_internal_cracks_or_t_junctions':True,'native_outer_boundary_complete':True,
                'independent_triangle_probes':probes,'maximum_probe_error_m':max_probe,
                'rms_probe_error_m':(sumsq/max(1,probes))**.5})
            out.write_text(json.dumps(report,indent=2)); print('FAR_AUDIT '+tile['id'],flush=True)
        report.update(passed=all(t['passed'] for t in rows),ended_unix=time.time(),shared_native_boundary_vertices_checked=shared,
            maximum_independent_probe_error_m=max(t['maximum_probe_error_m'] for t in rows),
            independent_triangle_probes=sum(t['independent_triangle_probes'] for t in rows),
            limits=['Finite vertex/interior probes do not certify a continuous maximum-error bound.',
                    'Geometric preparation only; native import, streaming, visual acceptance and performance remain unverified.'])
    except BaseException as e:
        report.update(error=repr(e),ended_unix=time.time()); out.write_text(json.dumps(report,indent=2)); raise
    out.write_text(json.dumps(report,indent=2))
    print(json.dumps({k:report[k] for k in ['build_id','passed','shared_native_boundary_vertices_checked','maximum_independent_probe_error_m','independent_triangle_probes']},indent=2))
    if not report['passed']: raise SystemExit(1)


if __name__=='__main__': main()
