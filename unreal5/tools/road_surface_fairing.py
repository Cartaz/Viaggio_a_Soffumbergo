"""Bound geometric pavement gradients without changing terrain source samples.

Nearest-axis height lookup can create steep triangular ridges at GIS corners,
even when the longitudinal profile is gentle. Project the shared pavement mesh
onto an explicit engineering gradient bound. This changes only derived asphalt
heights, with a measured correction limit; it does not alter the vehicle.
"""
import argparse
import json
from pathlib import Path
import numpy as np


def fair_pavement(chunks, maximum_grade, maximum_delta, *, iterations=10000, tolerance=.001):
    counts=[len(c['vertices']) for c in chunks]
    vertices=np.concatenate([c['vertices'] for c in chunks])
    # Builder convention: X east, second column height, third column south.
    xy,inv=np.unique(np.round(vertices[:,[0,2]],6),axis=0,return_inverse=True)
    count=np.bincount(inv,minlength=len(xy))
    h=np.bincount(inv,weights=vertices[:,1],minlength=len(xy))/count
    initial=h.copy();faces=[];start=0
    for c,n in zip(chunks,counts):
        faces.append(inv[start+np.asarray(c['triangles'])]);start+=n
    faces=np.concatenate(faces)
    t=xy[faces];ab=t[:,1]-t[:,0];ac=t[:,2]-t[:,0]
    den=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
    if np.any(np.abs(den)<1.e-14):raise ValueError('Degenerate planar pavement face')
    degree=np.bincount(faces.ravel(),minlength=len(xy))
    operator=np.stack([np.stack([t[:,1,1]-t[:,2,1],t[:,2,1]-t[:,0,1],t[:,0,1]-t[:,1,1]],axis=1),
                       np.stack([t[:,2,0]-t[:,1,0],t[:,0,0]-t[:,2,0],t[:,1,0]-t[:,0,0]],axis=1)],axis=1)/den[:,None,None]
    # The exact closest-height projection is anisotropic for skinny faces.
    # Scaling both gradient components indiscriminately changes the long-axis
    # slope unnecessarily and can fail to converge along fine boundaries.
    basis,singular,_=np.linalg.svd(operator,full_matrices=False)
    eigen=singular*singular
    def gradients(values,ids):
        z=values[faces[ids]];b=z[:,1]-z[:,0];c=z[:,2]-z[:,0]
        gx=(b*ac[ids,1]-c*ab[ids,1])/den[ids]
        gy=(ab[ids,0]*c-ac[ids,0]*b)/den[ids]
        return z,np.column_stack([gx,gy]),np.hypot(gx,gy)
    all_ids=np.arange(len(faces))
    _,_,norm=gradients(h,all_ids)
    initial_max=float(norm.max());initial_bad=int(np.count_nonzero(norm>maximum_grade+tolerance))
    cached_norm=norm.copy()
    active=np.flatnonzero(norm>maximum_grade+tolerance)
    # Only faces incident to changed vertices can violate a previously satisfied
    # bound. Maintain that exact active set instead of rescanning half a million
    # untouched faces in every projection step.
    order=np.argsort(faces.ravel(),kind='stable')
    incident=np.repeat(all_ids,3)[order]
    pointers=np.r_[0,np.cumsum(degree)]
    for iteration in range(iterations):
        z,g,norm=gradients(h,active)
        cached_norm[active]=norm
        over=norm>maximum_grade+tolerance
        if not over.any():break
        bad=active[over]
        u=basis[bad];e=eigen[bad]
        r=np.einsum('nji,nj->ni',u,g[over]);lagrange=np.zeros(len(r))
        for _ in range(36):
            denominator=1+lagrange[:,None]*e
            reduced=r/denominator;length=np.linalg.norm(reduced,axis=1)
            derivative=np.sum(reduced*reduced*e/denominator,axis=1)
            lagrange+=np.maximum(0,length-maximum_grade)*length/np.maximum(derivative,1.e-30)
        dual=np.einsum('nij,nj->ni',u,lagrange[:,None]*r/(1+lagrange[:,None]*e))
        delta=-np.einsum('nki,nk->ni',operator[bad],dual)
        changed,inverse=np.unique(faces[bad].ravel(),return_inverse=True)
        correction=np.bincount(inverse,weights=delta.ravel(),minlength=len(changed))
        h[changed]+=correction/degree[changed]
        starts=pointers[changed];sizes=degree[changed]
        indices=np.repeat(starts,sizes)+np.arange(int(sizes.sum()))-np.repeat(np.r_[0,np.cumsum(sizes)[:-1]],sizes)
        active=np.unique(incident[indices])
        if iteration%200==0:print('PAVEMENT_PROJECT iteration='+str(iteration)+' bad='+str(len(bad))+' max_grade='+str(float(cached_norm.max())),flush=True)
    else:raise RuntimeError('Pavement projection did not converge: max_grade='+str(float(cached_norm.max()))+'; retain draft for review')
    _,_,norm=gradients(h,all_ids)
    if norm.max()>maximum_grade+tolerance:raise RuntimeError('Global pavement verification failed after active-set convergence')
    change=h-initial
    if np.max(np.abs(change))>maximum_delta:raise RuntimeError('Pavement correction exceeds declared engineering bound')
    start=0
    for c,n in zip(chunks,counts):
        c['vertices'][:,1]=h[inv[start:start+n]];start+=n
    return {'method':'Shared-vertex projection of actual pavement triangles onto a gradient bound; no source-raster or vehicle edit',
            'maximum_grade':maximum_grade,'numeric_grade_tolerance':tolerance,
            'initial_maximum_triangle_grade':initial_max,'initial_faces_over_bound':initial_bad,
            'final_maximum_triangle_grade':float(norm.max()),'iterations':iteration,
            'max_height_correction_m':float(np.max(np.abs(change))),
            'rms_height_correction_m':float(np.sqrt(np.mean(change*change))),
            'changed_shared_vertices':int(np.count_nonzero(np.abs(change)>1.e-6)),
            'shared_vertices':len(xy),'pavement_triangles':len(faces),
            'source_rasters_modified':False,'physically_driven':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise RuntimeError('Preserve previous projection preflight')
    m=json.loads(args.manifest.read_text());chunks=[]
    for item in m['meshes']:
        if item['kind']!='asphalt':continue
        data=json.loads(Path(item['source']).read_text())
        ue=(np.asarray(data['vertices_cm'])+np.asarray(item['location_cm']))/100
        chunks.append({'vertices':ue[:,[0,2,1]],'triangles':np.asarray(data['triangles'])})
    report=fair_pavement(chunks,.24,.75)
    report.update({'reference_build_id':m['build_id'],'world_modified':False,'preview_only':True})
    args.output.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
