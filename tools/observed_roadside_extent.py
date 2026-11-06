"""Clip engineered local runs to observed topology, without claiming survey data."""
import copy
import math
import numpy as np


def frame(rule):
    origin=np.asarray(rule['frame_origin_UE_xy_m'],float)
    axis=np.asarray(rule['forward_UE_xy_unit'],float);axis/=np.linalg.norm(axis)
    return origin,axis


def clip_segment(a,b,rule):
    origin,axis=frame(rule);sa=float((a-origin)@axis);sb=float((b-origin)@axis)
    t0,t1=0.,1.;delta=sb-sa
    for bound,lower in [(rule.get('minimum_forward_m'),True),(rule.get('maximum_forward_m'),False)]:
        if bound is None:continue
        if abs(delta)<1.e-12:
            if (sa<bound if lower else sa>bound):return None
            continue
        crossing=(bound-sa)/delta
        if (delta>0)==lower:t0=max(t0,crossing)
        else:t1=min(t1,crossing)
    if t1-t0<1.e-8:return None
    return a+(b-a)*t0,a+(b-a)*t1


def terminal_side(q,rule):
    origin,axis=frame(rule);s=float((q-origin)@axis)
    if rule.get('minimum_forward_m') is not None and abs(s-rule['minimum_forward_m'])<1.e-6:return -1
    if rule.get('maximum_forward_m') is not None and abs(s-rule['maximum_forward_m'])<1.e-6:return 1
    return None


def rounded_terminal(section,open_direction,length,segments):
    """Six closed convex lofts approximate the observed rolled terminal nose.

    Dimensions remain engineering parameters. The first rectangle is identical
    to the rail joint, and no invisible collision extension is introduced.
    """
    center=np.asarray(section['center']);normal=np.asarray(section['normal'])
    middle=(section['bottom']+section['top'])/2;half=(section['top']-section['bottom'])/2
    sections=[copy.deepcopy(section)]
    for i in range(1,segments+1):
        theta=(math.pi/2-.03)*i/segments
        scale=math.cos(theta)
        sections.append({'center':center+open_direction*length*math.sin(theta),
            'normal':normal*scale,'bottom':middle-half*scale,'top':middle+half*scale,'height':section['height']})
    return sections
