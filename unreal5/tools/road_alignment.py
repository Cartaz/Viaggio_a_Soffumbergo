"""Bounded derived-axis corrections at three independently observed road banks.

The source OSM file is immutable. The DTM scores a geometric design alternative;
it does not turn the resulting road width or axis into surveyed pavement data.
"""
import math
import numpy as np


def align_observed_benches(profile, raw, sample, config):
    xy=np.asarray(profile[:-1])[:,[0,2]]
    levels=np.asarray(profile[:-1])[:,1]
    corrected=np.asarray(raw).copy()
    shifts=np.zeros_like(xy)
    reports=[]
    directions=np.roll(xy,-2,axis=0)-np.roll(xy,2,axis=0)
    norms=np.linalg.norm(directions,axis=1)
    directions/=np.maximum(norms[:,None],1.e-9)
    normals=np.column_stack([-directions[:,1],directions[:,0]])
    segment_lengths=np.linalg.norm(np.roll(xy,-1,axis=0)-xy,axis=1)
    for control in config['controls']:
        anchor=np.asarray(control['axis_UE_xy_m'])
        nearest=int(np.argmin(np.linalg.norm(xy-anchor,axis=1)))
        if np.linalg.norm(xy[nearest]-anchor)>.05:raise ValueError('Reviewed source anchor changed: '+control['id'])
        dist=np.linalg.norm(xy-anchor,axis=1)
        radius=config['transition_radius_m']
        eligible=dist<radius
        if eligible[0] or eligible[-1]:raise ValueError('A reviewed bank must not cross route start')
        if np.any((np.linalg.norm(shifts,axis=1)>1.e-6)&eligible):
            raise ValueError('Overlapping reviewed corrections require a joint design')
        runs=np.split(np.flatnonzero(eligible),np.flatnonzero(np.diff(np.flatnonzero(eligible))>1)+1)
        # Native support cells extend beyond the asphalt footprint. Include
        # their corners in the score instead of optimizing only the centre.
        half=config['carriageway_width_m']/2+.5*math.sqrt(2)
        cross=np.linspace(-half,half,25)
        max_shift=config['maximum_lateral_shift_m']
        choices=np.arange(-max_shift,max_shift+1.e-6,config['shift_search_step_m'])
        zero=int(np.argmin(np.abs(choices)))
        for run in runs:
            ids=np.arange(run[0]-1,run[-1]+2)
            norm=normals[ids]
            candidate=xy[ids,None,None,:]+(choices[None,:,None,None]+cross[None,None,:,None])*norm[:,None,None,:]
            height=sample(candidate[:,:,:,0],candidate[:,:,:,1])
            error=height-levels[ids,None,None]
            costs=np.mean(error*error,axis=2)+.3*np.max(error*error,axis=2)+.01*choices[None,:]**2
            costs[~np.isfinite(costs)]=np.inf
            # A slope-bound transition to the unchanged road is part of the
            # optimization. The zero-offset path is always feasible.
            envelope=max_shift*(.5+.5*np.cos(np.minimum(dist[ids]/radius,1)*math.pi))
            costs[np.abs(choices[None,:])>envelope[:,None]+1.e-8]=np.inf
            costs[[0,-1],:]=np.inf;costs[[0,-1],zero]=0
            history=[];value=costs[0].copy()
            vectors=choices[None,:,None]*norm[:,None,:]
            for row in range(1,len(ids)):
                delta=vectors[row,:,None,:]-vectors[row-1,None,:,:]
                distance=np.linalg.norm(delta,axis=2)
                limit=.04*segment_lengths[ids[row-1]]
                options=value[None,:]+20*distance*distance
                options[distance>limit+1.e-8]=np.inf
                previous=np.argmin(options,axis=1)
                value=costs[row]+options[np.arange(len(choices)),previous]
                history.append(previous)
            if not np.isfinite(value[zero]):raise ValueError('No bounded alignment path through source samples')
            state=zero;selected=[state]
            for previous in history[::-1]:state=int(previous[state]);selected.append(state)
            selected=selected[::-1]
            proposed=vectors[np.arange(len(ids)),selected]
            # Smooth vector changes without introducing any extra displacement.
            kernel=np.array([1,2,3,4,5,4,3,2,1],float)/25
            proposed=np.column_stack([np.convolve(np.pad(proposed[:,j],4),kernel,'valid') for j in range(2)])
            proposed[[0,-1]]=0
            # The source samples are not exactly equally spaced. Project back
            # onto the actual spatial slope bound after smoothing.
            for _ in range(12):
                for order in [range(1,len(ids)),range(len(ids)-2,-1,-1)]:
                    for row in order:
                        previous=row-1 if isinstance(order,range) and order.step>0 else row+1
                        length=segment_lengths[min(ids[row],ids[previous])]
                        d=proposed[row]-proposed[previous];mag=np.linalg.norm(d)
                        limit=config['maximum_shift_gradient']*.98*length
                        if mag>limit:proposed[row]=proposed[previous]+d*(limit/mag)
                proposed[[0,-1]]=0
            shifts[ids]+=proposed
        central=np.flatnonzero(dist<=config['central_review_radius_m'])
        def deviations(displacement):
            p=xy[central,None,:]+displacement[central,None,:]+cross[None,:,None]*normals[central,None,:]
            error=sample(p[:,:,0],p[:,:,1])-levels[central,None]
            return float(np.sqrt(np.mean(error*error))),float(np.max(np.abs(error)))
        before=deviations(np.zeros_like(shifts));after=deviations(shifts)
        reports.append({'id':control['id'],'source_anchor_index':nearest,
                        'anchor_UE_xy_m':anchor.tolist(),'selected_anchor_shift_UE_m':shifts[nearest].tolist(),
                        'candidate_rms_before_m':before[0],'candidate_rms_after_m':after[0],
                        'candidate_max_abs_before_m':before[1],'candidate_max_abs_after_m':after[1],
                        'central_axis_samples':len(central),'transition_radius_m':radius,
                        'status':'Variable bounded geometric alignment; requires native driving and surface checks'})
    gradient=np.linalg.norm(np.roll(shifts,-1,axis=0)-shifts,axis=1)/segment_lengths
    if gradient.max()>config['maximum_shift_gradient']:raise ValueError('Alignment transition is too abrupt')
    changed=np.linalg.norm(shifts,axis=1)>1.e-8
    corrected[:,0]+=shifts[:,0];corrected[:,2]+=shifts[:,1]
    corrected[changed,1]=sample(corrected[changed,0],corrected[changed,2])
    if not np.isfinite(corrected).all():raise ValueError('Alignment left measured terrain')
    return corrected,{'method':config['status'],'controls':reports,
                      'max_shift_m':float(np.linalg.norm(shifts,axis=1).max()),
                      'max_shift_gradient':float(gradient.max()),
                      'changed_axis_samples':int(changed.sum()),
                      'road_width_changed':False,'source_geometry_file_changed':False,
                      'native_imported':False,'physically_driven':False}
