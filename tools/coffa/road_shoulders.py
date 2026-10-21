"""A continuous collision ramp from actual road mesh edges to the derived ground."""
import numpy as np
import shapely
from shapely import STRtree


def conforming_triangles(part, offset, precision=.0001):
    """Clip to every ground triangle so soil cannot pierce a long shoulder face."""
    ox, oz = offset
    x, z = np.meshgrid(ox+np.arange(64)*2, oz+np.arange(64)*2)
    a = np.column_stack([x.ravel(), z.ravel()])
    triangles = np.concatenate([np.stack([a, a+[2, 0], a+[0, 2]], axis=1),
                                np.stack([a+[2, 0], a+[2, 2], a+[0, 2]], axis=1)])
    # 0.1 mm snap removes GEOS slivers while remaining far below suspension resolution.
    parts = shapely.intersection(shapely.polygons(triangles), part, grid_size=precision)
    parts = parts[shapely.area(parts) > precision**2]
    faces = shapely.get_parts(shapely.constrained_delaunay_triangles(parts))
    coords = shapely.get_coordinates(faces).reshape(-1, 4, 2)[:, :3]
    vertices, inverse = np.unique(np.round(coords.reshape(-1, 2), 6), axis=0, return_inverse=True)
    indices = inverse.reshape(-1, 3)
    # x/z orientation is opposite the y component of a 3D cross product.
    p = vertices[indices]
    cross = (p[:, 1, 0]-p[:, 0, 0])*(p[:, 2, 1]-p[:, 0, 1])-(p[:, 1, 1]-p[:, 0, 1])*(p[:, 2, 0]-p[:, 0, 0])
    indices[cross < 0] = indices[cross < 0, ::-1]
    return vertices, indices


class EdgeIndex:
    def __init__(self, edges):
        self.edges = np.asarray(edges, dtype=float)
        self.a = self.edges[:, 0, [0, 2]]
        self.delta = self.edges[:, 1, [0, 2]]-self.a
        self.den = (self.delta**2).sum(axis=1)
        self.tree = STRtree(shapely.linestrings(self.edges[:, :, [0, 2]]))

    def sample(self, x, z):
        q = np.column_stack([np.ravel(x), np.ravel(z)])
        pairs = self.tree.query_nearest(shapely.points(q), all_matches=False)
        ids = np.empty(len(q), dtype=int)
        ids[pairs[0]] = pairs[1]
        t = np.clip(((q-self.a[ids])*self.delta[ids]).sum(axis=1)/self.den[ids], 0, 1)
        nearest = self.a[ids]+t[:, None]*self.delta[ids]
        distance = np.linalg.norm(q-nearest, axis=1)
        heights = self.edges[ids, 0, 1]+t*(self.edges[ids, 1, 1]-self.edges[ids, 0, 1])
        return distance, heights


def ramp_height(distance, road, ground, width, cover=.03):
    """Zero blend derivative at both ends; don't put the ramp below existing soil."""
    t = np.clip(np.asarray(distance)/width, 0, 1)
    blend = t*t*(3-2*t)
    h = np.asarray(road)*(1-blend)+np.asarray(ground)*blend
    return np.maximum(h, np.asarray(ground)+cover*np.sin(np.pi*t)**2)


def terrain_height(chunks, x, z):
    """The same two triangles per 2 m cell as circuit_mesh.gd, never nearest-cell."""
    x, z = np.broadcast_arrays(x, z)
    q = np.column_stack([x.ravel(), z.ravel()])
    keys = np.floor(q/128).astype(int)*128
    result = np.full(len(q), np.nan)
    for key in np.unique(keys, axis=0):
        ids = np.where((keys == key).all(axis=1))[0]
        chunk = chunks.get(tuple(key))
        if chunk is None:
            # Exact far tile border belongs to the available neighboring tile.
            for delta in [(-128, 0), (0, -128), (-128, -128)]:
                alternative = tuple(key+delta)
                if alternative in chunks and np.all(q[ids] >= alternative) and np.all(q[ids] <= np.array(alternative)+128):
                    chunk = chunks[alternative]
                    key = np.array(alternative)
                    break
        if chunk is None:
            continue
        h = np.asarray(chunk['heights_m'], dtype=float).reshape(65, 65)
        local = (q[ids]-key)/2
        cell = np.clip(np.floor(local).astype(int), 0, 63)
        uv = local-cell
        c, r = cell[:, 0], cell[:, 1]
        lo = h[r, c]+uv[:, 0]*(h[r, c+1]-h[r, c])+uv[:, 1]*(h[r+1, c]-h[r, c])
        hi = h[r+1, c+1]+(1-uv[:, 0])*(h[r+1, c]-h[r+1, c+1])+(1-uv[:, 1])*(h[r, c+1]-h[r+1, c+1])
        result[ids] = np.where(uv.sum(axis=1) <= 1, lo, hi)
    return result.reshape(x.shape)
