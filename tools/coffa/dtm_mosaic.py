"""Explicit source selection; no blending, datum correction or missing-cell filling."""
import math


def interior_margin(east, north, bounds):
    west, south, right, top = bounds
    return min(east-west, right-east, north-south, top-north)


def choose_source(candidates):
    """Candidates: (filename, height, edge_margin, Valle_priority)."""
    if not candidates:
        return None
    return min(candidates, key=lambda c: (-int(c[3]), -c[2], c[0]))


def corridor_sectors(points, size, radius):
    """Select all boxes within radius of densely sampled route, no corner shortcut."""
    result = set()
    reach = math.ceil(radius/size)+1
    for x, z in points:
        col, row = math.floor(x/size), math.floor(z/size)
        for r in range(row-reach, row+reach+1):
            for c in range(col-reach, col+reach+1):
                a, b = c*size, r*size
                dx, dz = max(a-x, 0, x-a-size), max(b-z, 0, z-b-size)
                if dx*dx+dz*dz <= radius*radius:
                    result.add((a,b))
    return sorted(result, key=lambda p: (p[1],p[0]))


def masked_lod_error(heights, side, stride):
    """Finite-only nested-grid error; unknown coarse cells stay holes."""
    error = 0.
    for r in range(side):
        for c in range(side):
            value = heights[r*side+c]
            i = min(r//stride*stride, side-1-stride)
            j = min(c//stride*stride, side-1-stride)
            a,b,d,e = [heights[k] for k in [i*side+j, i*side+j+stride,
                                            (i+stride)*side+j,(i+stride)*side+j+stride]]
            if value is None or any(h is None for h in (a,b,d,e)):
                continue
            u,v = (c-j)/stride,(r-i)/stride
            estimate = a+(b-a)*u+(d-a)*v if u+v <= 1 else e+(d-e)*(1-u)+(b-e)*(1-v)
            error = max(error,abs(value-estimate))
    return error


class Mosaic:
    def __init__(self, tiles, arrays, origin, primary_names=(), primary_region=None):
        order = sorted(range(len(tiles)), key=lambda i:tiles[i]['filename'])
        self.tiles = [tiles[i] for i in order]
        self.arrays = [arrays[i] for i in order]
        self.origin = origin
        self.primary_names = set(primary_names)
        self.primary_region = primary_region

    def sample(self, local_x, local_z):
        """Vectorized cell-centre bilinear samples, winning source IDs and source spread."""
        import numpy as np
        x,z = np.broadcast_arrays(np.asarray(local_x,dtype=float),np.asarray(local_z,dtype=float))
        east,north = self.origin[0]+x,self.origin[1]-z
        chosen = np.full(x.shape,np.nan)
        source = np.full(x.shape,-1,dtype=np.int16)
        score = np.full(x.shape,-np.inf)
        priority = np.full(x.shape,-1,dtype=np.int8)
        low,high = np.full(x.shape,np.inf),np.full(x.shape,-np.inf)
        pinned = np.zeros(x.shape,dtype=bool)
        if self.primary_region:
            a,b,c,d = self.primary_region
            pinned = (x >= a)&(x <= c)&(z >= b)&(z <= d)
        for index,(tile,grid) in enumerate(zip(self.tiles,self.arrays)):
            west,south,right,top = tile['bounds_EN_m']
            rows,cols = grid.shape
            inside = (east >= west+.25)&(east <= right-.25)&(north >= south+.25)&(north <= top-.25)
            if not inside.any():
                continue
            ec,nc = east[inside],north[inside]
            col,row = (ec-west)/.5-.5,(top-nc)/.5-.5
            j,i = np.minimum(col.astype(int),cols-2),np.minimum(row.astype(int),rows-2)
            u,v = col-j,row-i
            a,b,c,d = [grid[rr,cc].astype(float) for rr,cc in [(i,j),(i,j+1),(i+1,j),(i+1,j+1)]]
            valid = np.isfinite(a+b+c+d)&(a!=-9999)&(b!=-9999)&(c!=-9999)&(d!=-9999)
            height = (1-v)*((1-u)*a+u*b)+v*((1-u)*c+u*d)
            margin = np.minimum.reduce([ec-west,right-ec,nc-south,top-nc])
            pri = (pinned[inside]&(tile['filename'] in self.primary_names)).astype(np.int8)
            win = valid&((pri > priority[inside])|((pri == priority[inside])&(margin > score[inside])))
            def put(target, values, mask):
                previous = target[inside]
                previous[mask] = values[mask] if hasattr(values,'shape') else values
                target[inside] = previous
            put(chosen,height,win)
            put(source,index,win)
            put(score,margin,win)
            put(priority,pri,win)
            put(low,np.minimum(low[inside],height),valid)
            put(high,np.maximum(high[inside],height),valid)
        spread = np.zeros(x.shape)
        valid = source >= 0
        spread[valid] = high[valid]-low[valid]
        return chosen-self.origin[2],source,spread
