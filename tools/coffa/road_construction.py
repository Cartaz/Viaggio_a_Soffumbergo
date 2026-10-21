"""Derived engineering geometry. Never infer a surveyed carriageway from the DTM.

The candidate axis is preserved, including retraced branches and reversals.
Planar union removes duplicate surfaces; constrained triangulation retains holes.
Spatial queries are bounded to the grading corridor, not vertices x full route.
"""
import math
import numpy as np
import shapely
from shapely import LineString, STRtree


def validate_config(config):
    for key in ['width_m', 'profile_radius_m', 'terrain_clearance_m', 'blend_m', 'mesh_max_edge_m']:
        if not math.isfinite(config[key]) or config[key] <= 0:
            raise ValueError('Positive finite construction parameter required: '+key)
    for key in ['surface_offset_m', 'shoulder_m', 'grade_warning', 'turn_warning_degrees', 'earthworks_review_m']:
        if not math.isfinite(config[key]) or config[key] < 0:
            raise ValueError('Nonnegative finite parameter required: '+key)
    if config['mesh_max_edge_m'] > config['width_m']:
        raise ValueError('Mesh edges must resolve the road width')


def design_profile(route, radius, offset):
    """Cyclic local linear fit, then one height per physical (possibly retraced) node."""
    raw = np.concatenate([np.asarray(f['points_m'])[:-1] for f in route])
    closed = np.vstack([raw, raw[0]])
    lengths = np.linalg.norm(np.diff(closed[:, [0, 2]], axis=0), axis=1)
    for index, f in enumerate(route):
        following = route[(index+1) % len(route)]['points_m'][0]
        if not np.allclose(f['points_m'][-1], following, atol=1e-6, rtol=0):
            raise ValueError('Candidate is not a connected closed route')
    if not np.isfinite(closed).all() or np.any(lengths < 1e-5):
        raise ValueError('Invalid or duplicate consecutive horizontal route point')
    station = np.r_[0, np.cumsum(lengths)]
    total = station[-1]
    extended_s = np.concatenate([station[:-1]-total, station[:-1], station[:-1]+total])
    extended_h = np.tile(raw[:, 1], 3)
    p = raw.copy()
    for i, s in enumerate(station[:-1]):
        lo, hi = np.searchsorted(extended_s, [s-radius, s+radius], side='left')
        a = np.column_stack([np.ones(hi-lo), extended_s[lo:hi]-s])
        p[i, 1] = np.linalg.lstsq(a, extended_h[lo:hi], rcond=None)[0][0]+offset
    groups = {}
    for i, xz in enumerate(np.round(p[:, [0, 2]], 6)):
        groups.setdefault(tuple(xz), []).append(i)
    max_spread = 0.0
    for ids in groups.values():
        max_spread = max(max_spread, float(np.ptp(p[ids, 1])))
        p[ids, 1] = p[ids, 1].mean()
    p = np.vstack([p, p[0]])
    tangent = np.diff(p[:, [0, 2]], axis=0)/lengths[:, None]
    angles = np.degrees(np.arccos(np.clip((tangent*np.roll(tangent, 1, axis=0)).sum(axis=1), -1, 1)))
    return p, raw, station, angles, {'repeated_node_count':len(raw)-len(groups),
                                    'max_unified_profile_spread_m':max_spread}


class SegmentIndex:
    def __init__(self, points):
        self.p = np.asarray(points, dtype=float)
        self.a = self.p[:-1, [0, 2]]
        self.delta = np.diff(self.p[:, [0, 2]], axis=0)
        self.den = (self.delta*self.delta).sum(axis=1)
        if np.any(self.den < 1e-10):
            raise ValueError('Degenerate segment')
        self.tree = STRtree([LineString([a, a+d]) for a, d in zip(self.a, self.delta)])

    def query(self, x, z, radius):
        """Exact nearest within radius; deterministic lowest segment index breaks ties.

        Outside the corridor: inf distance, NaN height, -1 segment. Callers must
        preserve the original terrain there. Separate parallel branches are never
        averaged. Shared/retraced node heights were unified in the design profile.
        """
        x, z = np.broadcast_arrays(x, z)
        q = np.column_stack([x.ravel(), z.ravel()])
        qi, si = self.tree.query(shapely.points(q), predicate='dwithin', distance=radius)
        distance = np.full(len(q), np.inf)
        height = np.full(len(q), np.nan)
        segment = np.full(len(q), -1, dtype=int)
        if len(qi):
            t = np.clip(((q[qi]-self.a[si])*self.delta[si]).sum(axis=1)/self.den[si], 0, 1)
            dist2 = ((q[qi]-self.a[si]-t[:, None]*self.delta[si])**2).sum(axis=1)
            order = np.lexsort((si, dist2, qi))
            first = order[np.r_[True, np.diff(qi[order]) != 0]]
            j, k = qi[first], si[first]
            distance[j] = np.sqrt(dist2[first])
            height[j] = self.p[k, 1]+t[first]*(self.p[k+1, 1]-self.p[k, 1])
            segment[j] = k
        return distance.reshape(x.shape), height.reshape(x.shape), segment.reshape(x.shape)


def road_footprint(points, width):
    if not math.isfinite(width) or width <= 0:
        raise ValueError('Invalid design width')
    # Rounded caps expose reversals without adding a fictional turning circle.
    geometry = LineString(np.asarray(points)[:, [0, 2]]).buffer(width/2, quad_segs=4,
                                                             cap_style='round', join_style='round')
    if not geometry.is_valid or geometry.geom_type != 'Polygon':
        raise ValueError('Construction footprint must be one valid connected polygon')
    return geometry


def triangulate_surface(polygon, index, max_edge, radius):
    """Constrained union mesh, with conforming subdivision of long interior edges.

    Boundary segmentization precedes triangulation. Adjacent chunks get the same
    boundary stations; only interior long edges require midpoint subdivision.
    """
    polygon = shapely.segmentize(polygon, max_edge)
    triangles = [np.asarray(t.exterior.coords)[:3] for t in
                 shapely.constrained_delaunay_triangles(polygon).geoms]
    if not triangles:
        return [], []
    faces = np.asarray(triangles)
    for _ in range(16):
        long = np.linalg.norm(faces-np.roll(faces, -1, axis=1), axis=2) > max_edge+1e-8
        if not long.any():
            break
        refined = list(faces[~long.any(axis=1)])
        for face, flags in zip(faces[long.any(axis=1)], long[long.any(axis=1)]):
            boundary = []
            for j in range(3):
                boundary.append(face[j])
                if flags[j]:
                    boundary.append((face[j]+face[(j+1) % 3])/2)
            center = face.mean(axis=0)
            refined.extend(np.array([center, p, boundary[(j+1) % len(boundary)]])
                           for j, p in enumerate(boundary))
        faces = np.asarray(refined)
    else:
        raise ValueError('Surface subdivision did not converge')
    # Quantization is global so adjacent 128 m chunks share bit-identical vertices.
    xz, inverse = np.unique(np.round(faces.reshape(-1, 2), 6), axis=0, return_inverse=True)
    _, heights, _ = index.query(xz[:, 0], xz[:, 1], radius)
    if not np.isfinite(heights).all():
        raise ValueError('Surface vertex outside candidate buffer')
    vertices = np.column_stack([xz[:, 0], np.round(heights, 6), xz[:, 1]])
    indices = inverse.reshape(-1, 3)
    v = vertices[indices]
    cross = np.cross(v[:, 1]-v[:, 0], v[:, 2]-v[:, 0])[:, 1]
    if np.any(np.abs(cross) < 1e-10):
        raise ValueError('Degenerate road face after quantization')
    indices[cross > 0] = indices[cross > 0, ::-1]
    return vertices.tolist(), indices.tolist()
