"""Conforming coarse fans with original fine boundary vertices and hole guards."""
import numpy as np
from bisect import bisect_left, bisect_right


def valid_cells(holes, stride):
    n = holes.shape[0]; starts = np.arange(0, n-1, stride)
    if (n-1) % stride: raise ValueError('Stride must divide tile quads')
    integral = np.pad((holes != 0).astype(np.int32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    x, y = np.meshgrid(starts, starts)
    count = integral[y+stride+1, x+stride+1]-integral[y, x+stride+1]-integral[y+stride+1, x]+integral[y, x]
    return count == 0


def approximation(height, stride):
    """Evaluate the actual fan triangles at every native integer grid point."""
    if stride == 1: return height.astype(float)
    n = len(height); yy, xx = np.indices(height.shape)
    x0 = np.minimum(xx//stride, (n-2)//stride)*stride
    y0 = np.minimum(yy//stride, (n-2)//stride)*stride
    fx = (xx-x0)/stride; fy = (yy-y0)/stride
    dx = fx-.5; dy = fy-.5; weight = np.maximum(np.abs(dx), np.abs(dy))*2
    qx = np.divide(dx, weight, out=np.zeros_like(dx), where=weight>0)+.5
    qy = np.divide(dy, weight, out=np.zeros_like(dy), where=weight>0)+.5
    a = height[y0, x0].astype(float); b = height[y0, x0+stride].astype(float)
    c = height[y0+stride, x0].astype(float); d = height[y0+stride, x0+stride].astype(float)
    top = (dy <= -np.abs(dx)); bottom = (dy >= np.abs(dx))
    left = ~(top | bottom) & (dx < 0)
    right = ~(top | bottom | left)
    edge = np.where(top, a+(b-a)*qx, np.where(bottom, c+(d-c)*qx, np.where(left, a+(c-a)*qy, b+(d-b)*qy)))
    # Boundary fans interpolate between all original edge samples, rather than
    # a long chord that could leave cracks next to the full Landscape.
    for selected, along, start, fixed, horizontal in [
        (top & (y0 == 0), qx, x0, 0, True),
        (bottom & (y0+stride == n-1), qx, x0, n-1, True),
        (left & (x0 == 0), qy, y0, 0, False),
        (right & (x0+stride == n-1), qy, y0, n-1, False)]:
        ids = np.nonzero(selected)
        t = start[ids]+along[ids]*stride
        i = np.minimum(np.floor(t).astype(int), n-2); f = t-i
        line = height[fixed, :] if horizontal else height[:, fixed]
        edge[ids] = line[i].astype(float)*(1-f)+line[i+1].astype(float)*f
    center = height[y0+stride//2, x0+stride//2].astype(float)
    return center*(1-weight)+edge*weight


def build_mesh(height, holes, stride, spacing_cm, quantum_cm, zero_cm):
    n = len(height); valid = valid_cells(holes, stride)
    vertices = []; faces = []; lookup = {}

    def vertex(x, y):
        key = (int(x), int(y))
        if key not in lookup:
            lookup[key] = len(vertices)
            vertices.append([x*spacing_cm, y*spacing_cm, float(height[y, x])*quantum_cm+zero_cm])
        return lookup[key]

    for row, col in np.argwhere(valid):
        x = int(col*stride); y = int(row*stride); s = stride
        if s == 1:
            a,b,c,d = vertex(x,y),vertex(x+1,y),vertex(x,y+1),vertex(x+1,y+1)
            faces.extend([[a,b,d],[a,d,c]])
            continue
        # Positive XY winding. The native importer must use its verified mesh
        # convention; this data artifact does not claim a rendered face test.
        ring = [(x,y)]
        ring += [(u,y) for u in range(x+1,x+s+1)] if y == 0 else [(x+s,y)]
        ring += [(x+s,v) for v in range(y+1,y+s+1)] if x+s == n-1 else [(x+s,y+s)]
        ring += [(u,y+s) for u in range(x+s-1,x-1,-1)] if y+s == n-1 else [(x,y+s)]
        ring += [(x,v) for v in range(y+s-1,y,-1)] if x == 0 else []
        ids = [vertex(*q) for q in ring]
        center = vertex(x+s//2,y+s//2)
        faces.extend([[center,a,b] for a,b in zip(ids, ids[1:]+ids[:1])])
    return np.array(vertices, dtype=np.float64).reshape(-1,3), np.array(faces, dtype=np.int32).reshape(-1,3), valid


def mesh_errors(height, holes, stride, quantum_m):
    valid = valid_cells(holes, stride)
    # Grid vertices shared by several coarse cells are included only if all
    # touching coarse cells survive. This keeps hole-edge errors conservative.
    yy, xx = np.indices(height.shape)
    iy = np.minimum(yy//stride, len(valid)-1); ix = np.minimum(xx//stride, len(valid)-1)
    selected = valid[iy, ix] & (holes == 0)
    if not np.any(selected): return {'max_error_m': 0.0, 'rms_error_m': 0.0, 'checked_samples': 0}
    error = (approximation(height, stride)[selected]-height[selected].astype(float))*quantum_m
    return {'max_error_m': float(np.max(np.abs(error))), 'rms_error_m': float(np.sqrt(np.mean(error*error))),
            'checked_samples': int(len(error))}


def adaptive_mesh(height, holes, strides, spacing_cm, quantum_cm, zero_cm, error_limit_m, _forced=None, _pass=0):
    """Refine local cells, then stitch each edge using shared native vertices.

    A refined edge can differ from the original cell fan by at most that fan's
    native-vertex error. A half-limit initial bound therefore leaves room for
    the conforming edges. The final sampled error is independently evaluated
    from emitted triangle barycentrics below.
    """
    n=len(height); largest=max(strides); limit=error_limit_m/2
    forced=set() if _forced is None else _forced
    if _pass>12: raise RuntimeError('Local refinement did not converge')
    if largest & (largest-1) or (n-1)%largest: raise ValueError('Power-of-two root cells dividing tile required')
    errors={}; validity={}
    for s in sorted(strides,reverse=True):
        validity[s]=valid_cells(holes,s)
        if s==1: continue
        error=np.abs(approximation(height,s)-height.astype(float))*(quantum_cm/100)
        cells=(n-1)//s; maximum=np.zeros((cells,cells))
        for dy in range(s+1):
            for dx in range(s+1):
                np.maximum(maximum,error[dy:dy+cells*s:s,dx:dx+cells*s:s],out=maximum)
        errors[s]=maximum
    leaves=[]; omitted=0

    def split(x,y,s):
        nonlocal omitted
        good=bool(validity[s][y//s,x//s])
        if not good and np.all(holes[y:y+s+1,x:x+s+1]!=0): omitted+=1; return
        if s==1:
            if good: leaves.append((x,y,s))
            else: omitted+=1
            return
        if good and errors[s][y//s,x//s] <= limit and (x,y,s) not in forced: leaves.append((x,y,s)); return
        half=s//2
        for dx,dy in [(0,0),(half,0),(0,half),(half,half)]: split(x+dx,y+dy,half)

    for y in range(0,n-1,largest):
        for x in range(0,n-1,largest): split(x,y,largest)
    horizontal={}; vertical={}
    for x,y,s in leaves:
        for xx,yy in [(x,y),(x+s,y),(x+s,y+s),(x,y+s)]:
            horizontal.setdefault(yy,set()).add(xx); vertical.setdefault(xx,set()).add(yy)
    for q in [0,n-1]:
        horizontal.setdefault(q,set()).update(range(n)); vertical.setdefault(q,set()).update(range(n))
    horizontal={k:sorted(v) for k,v in horizontal.items()}; vertical={k:sorted(v) for k,v in vertical.items()}
    vertices=[]; faces=[]; sample_xy=[]; lookup={}; leaf_rows=[]
    max_error=0.; sum_squared=0.; checked=0

    def vertex(x,y):
        key=(x,y)
        if key not in lookup:
            lookup[key]=len(vertices); sample_xy.append(key)
            vertices.append([x*spacing_cm,y*spacing_cm,float(height[y,x])*quantum_cm+zero_cm])
        return lookup[key]

    def interval(data,a,b): return data[bisect_left(data,a):bisect_right(data,b)]

    for x,y,s in leaves:
        start=len(faces)
        if s==1:
            a,b,c,d=vertex(x,y),vertex(x+1,y),vertex(x,y+1),vertex(x+1,y+1)
            faces.extend([[a,b,d],[a,d,c]])
        else:
            top=interval(horizontal[y],x,x+s); right=interval(vertical[x+s],y,y+s)
            bottom=interval(horizontal[y+s],x,x+s); left=interval(vertical[x],y,y+s)
            ring=[(u,y) for u in top]+[(x+s,v) for v in right[1:]]+[(u,y+s) for u in bottom[-2::-1]]+[(x,v) for v in left[-2:0:-1]]
            ids=[vertex(*p) for p in ring]; center=vertex(x+s//2,y+s//2)
            faces.extend([[center,a,b] for a,b in zip(ids,ids[1:]+ids[:1])])
        count=len(faces)-start; leaf_rows.append([x,y,s,start,count])
        # Independent geometric evaluator of the emitted triangles, including
        # original vertices on their interiors, rather than the fan formula.
        yy,xx=np.mgrid[y:y+s+1,x:x+s+1]; points=np.column_stack([xx.ravel(),yy.ravel()])
        predicted=np.full(len(points),np.nan)
        for face in faces[start:]:
            tri=np.array([sample_xy[i] for i in face],float); z=np.array([height[b,a] for a,b in tri.astype(int)],float)
            a=tri[0]; ab=tri[1]-a; ac=tri[2]-a; q=points-a
            den=ab[0]*ac[1]-ab[1]*ac[0]
            u=(q[:,0]*ac[1]-q[:,1]*ac[0])/den; v=(ab[0]*q[:,1]-ab[1]*q[:,0])/den
            yes=(u>=-1e-10)&(v>=-1e-10)&(u+v<=1+1e-10)
            predicted[yes]=z[0]+u[yes]*(z[1]-z[0])+v[yes]*(z[2]-z[0])
        if np.any(~np.isfinite(predicted)): raise RuntimeError('Uncovered point inside retained cell')
        error=(predicted-height[points[:,1],points[:,0]].astype(float))*(quantum_cm/100)
        max_error=max(max_error,float(np.max(np.abs(error))))
        sum_squared+=float(error@error); checked+=len(error)
    if max_error>error_limit_m+1e-8: raise RuntimeError('Conforming mesh exceeds final native-vertex bound: '+str(max_error))
    va=np.array(vertices,float).reshape(-1,3); fa=np.array(faces,np.int32).reshape(-1,3)
    grid=np.array(sample_xy,np.int32).reshape(-1,2); leaf_array=np.array(leaf_rows,np.int32).reshape(-1,5)
    tri=grid[fa]; bad=np.zeros(len(fa),bool); max_probe=0.
    for weights in [[1/3,1/3,1/3],[.5,.5,0],[.5,0,.5],[0,.5,.5]]:
        weights=np.array(weights); point=tri.transpose(0,2,1)@weights
        ix=np.minimum(np.floor(point[:,0]).astype(int),n-2); iy=np.minimum(np.floor(point[:,1]).astype(int),n-2)
        fx=point[:,0]-ix; fy=point[:,1]-iy
        a=height[iy,ix].astype(float); b=height[iy,ix+1].astype(float)
        c=height[iy+1,ix].astype(float); d=height[iy+1,ix+1].astype(float)
        exact=np.where(fx>=fy,a+(b-a)*fx+(d-b)*fy,a+(d-c)*fx+(c-a)*fy)*quantum_cm+zero_cm
        error=np.abs(va[fa,2]@weights-exact)/100
        bad|=error>error_limit_m+1e-8; max_probe=max(max_probe,float(np.max(error,initial=0)))
    if np.any(bad):
        affected=np.unique(np.searchsorted(leaf_array[:,3],np.flatnonzero(bad),side='right')-1)
        extra={tuple(int(v) for v in leaf_array[i,:3]) for i in affected}
        if any(s==1 for x,y,s in extra): raise RuntimeError('Native triangles failed interior check')
        return adaptive_mesh(height,holes,strides,spacing_cm,quantum_cm,zero_cm,error_limit_m,forced|extra,_pass+1)
    return (va,fa,grid,leaf_array,
        {'max_error_m':max_error,'rms_error_m':(sum_squared/max(1,checked))**.5,'checked_samples_including_shared_vertices':checked,
         'maximum_triangle_probe_error_m':max_probe,'interior_refinement_passes':_pass,
         'leaf_cells':len(leaves),'omitted_cells':omitted,'leaf_stride_counts':{str(s):sum(q[2]==s for q in leaves) for s in strides}})
