"""Conservative native heightfield support under an exact triangle road surface.

A Landscape vertex contributes to the four adjacent cells. Capping only the
height at the vertex misses a road edge or a curved junction inside a cell.
For every vertex, bound all asphalt planes over their actual intersection with
those cells. Linear interpolation of capped vertices then stays below asphalt.
This is subgrade engineering in the derived world, never a new LiDAR reading.
"""
import numpy as np
import shapely


def support_caps(x, y, faces, tree, polygons, step_m, clearance_m, chunk=4096):
    x, y = np.broadcast_arrays(x, y)
    result = np.full(x.size, np.inf)
    px, py = x.ravel(), y.ravel()
    for start in range(0, len(px), chunk):
        end = min(start + chunk, len(px))
        cells = shapely.box(px[start:end]-step_m, py[start:end]-step_m,
                            px[start:end]+step_m, py[start:end]+step_m)
        pairs = tree.query(cells, predicate='intersects')
        if not pairs.size:
            continue
        clipped = shapely.intersection(cells[pairs[0]], polygons[pairs[1]])
        coordinates, owners = shapely.get_coordinates(clipped, return_index=True)
        if not len(coordinates):
            continue
        chosen = pairs[1, owners]
        tri = faces[chosen]
        a = tri[:, 0, [0, 2]]
        ab = tri[:, 1, [0, 2]]-a
        ac = tri[:, 2, [0, 2]]-a
        q = coordinates-a
        den = ab[:, 0]*ac[:, 1]-ab[:, 1]*ac[:, 0]
        valid = np.abs(den) > 1.e-12
        u = np.zeros(len(q)); v = u.copy()
        u[valid] = (q[valid, 0]*ac[valid, 1]-q[valid, 1]*ac[valid, 0])/den[valid]
        v[valid] = (ab[valid, 0]*q[valid, 1]-ab[valid, 1]*q[valid, 0])/den[valid]
        height = tri[:, 0, 1]+u*(tri[:, 1, 1]-tri[:, 0, 1])+v*(tri[:, 2, 1]-tri[:, 0, 1])
        np.minimum.at(result, start+pairs[0, owners[valid]], height[valid]-clearance_m)
    return result.reshape(x.shape)
