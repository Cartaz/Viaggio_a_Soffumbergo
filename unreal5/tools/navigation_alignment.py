"""Transfer documented route points to a versioned derived road alignment."""
import numpy as np
import shapely


def on_derived_axis(points_cm, manifest):
    if 'source_reference_profile_UE_cm' not in manifest:
        return points_cm, {'applied':False,'maximum_shift_m':0.}
    old=np.asarray(manifest['source_reference_profile_UE_cm'])[:,:2]
    new=np.asarray(manifest['profile_UE_cm'])[:,:2]
    if old.shape!=new.shape:raise ValueError('Source/derived axis correspondence is missing')
    a=old[:-1];d=np.diff(old,axis=0);den=(d*d).sum(axis=1)
    tree=shapely.STRtree(shapely.linestrings(np.stack([old[:-1],old[1:]],axis=1)))
    pairs,distance=tree.query_nearest(shapely.points(points_cm),all_matches=True,return_distance=True)
    if distance.max()>.2:raise ValueError('Navigation reference is not on the original candidate axis')
    pids,segments=pairs
    t=np.clip(((points_cm[pids]-a[segments])*d[segments]).sum(axis=1)/den[segments],0,1)
    delta=new-old
    shifted=points_cm[pids]+delta[segments]+t[:,None]*(delta[segments+1]-delta[segments])
    low=np.full((len(points_cm),2),np.inf);high=np.full((len(points_cm),2),-np.inf)
    np.minimum.at(low,pids,shifted);np.maximum.at(high,pids,shifted)
    spread=np.linalg.norm(high-low,axis=1)
    if spread.max()>.02:raise ValueError('Shared/retraced source node has conflicting derived alignments')
    rows,first=np.unique(pids,return_index=True)
    if len(rows)!=len(points_cm):raise ValueError('Unmapped navigation point')
    result=np.empty_like(points_cm);result[rows]=shifted[first]
    return result,{'applied':True,'maximum_shift_m':float(np.linalg.norm(result-points_cm,axis=1).max()/100),
                  'maximum_shared_reference_spread_cm':float(spread.max()),
                  'source_reference_max_distance_cm':float(distance.max()),
                  'method':'Nearest source segment with checked shared-node consistency; interpolate its derived displacement. No original source file edit.',
                  'physically_driven':False}
