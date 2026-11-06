"""Shared cross-sections and exact convex faces for roadside solid joints."""
from itertools import combinations
import numpy as np


def convex_faces(vertices):
    v=np.asarray(vertices,dtype=float);p=v-v.mean(axis=0);planes={};tol=1.e-8
    for a,b,c in combinations(range(len(p)),3):
        normal=np.cross(p[b]-p[a],p[c]-p[a]);length=np.linalg.norm(normal)
        if length<1.e-12:continue
        normal/=length;distance=(p-p[a])@normal
        if distance.max()>tol and distance.min()<-tol:continue
        if distance.max()>tol:normal=-normal;distance=-distance
        members=tuple(np.flatnonzero(np.abs(distance)<=tol))
        planes.setdefault(members,normal)
    faces=[]
    for members,normal in planes.items():
        q=p[list(members)];center=q.mean(axis=0);axis=q[0]-center;axis/=np.linalg.norm(axis)
        other=np.cross(normal,axis);angle=np.arctan2((q-center)@other,(q-center)@axis)
        order=np.asarray(members)[np.argsort(angle)]
        for i in range(1,len(order)-1):faces.append([int(order[0]),int(order[i]),int(order[i+1])])
    result=np.asarray(faces,dtype=int)
    if len(result)!=12 or len(set(result.ravel()))!=8:raise ValueError('Roadside solid is not a convex eight-corner prism')
    return result


def joined_prism(sections,width):
    """Reuse both end rectangles verbatim; rendered faces equal collision hull."""
    a,b=sections
    inner0=a['center']-a['normal']*width/2;outer0=a['center']+a['normal']*width/2
    inner1=b['center']-b['normal']*width/2;outer1=b['center']+b['normal']*width/2
    xy=np.asarray([inner0,inner1,outer1,outer0])
    return np.vstack([np.column_stack([xy,[a['bottom'],b['bottom'],b['bottom'],a['bottom']]]),
        np.column_stack([xy,[a['top'],b['top'],b['top'],a['top']]])])
