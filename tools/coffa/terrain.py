"""Terrain geometry in the native projected frame. No implicit datum conversion."""
import math


def sample_grid(grid, east, north, west, top, resolution=.5):
    """Bilinear sample at ASC cell CENTRES; reject out-of-coverage requests."""
    col = (east - west) / resolution - .5
    row = (top - north) / resolution - .5
    rows, cols = len(grid), len(grid[0])
    if not (0 <= col <= cols - 1 and 0 <= row <= rows - 1):
        raise ValueError("Point outside cell-centre coverage")
    i, j = min(int(row), rows - 2), min(int(col), cols - 2)
    v, u = row - i, col - j
    values = [float(grid[i][j]), float(grid[i][j + 1]),
              float(grid[i + 1][j]), float(grid[i + 1][j + 1])]
    if any(not math.isfinite(h) or h == -9999 for h in values):
        raise ValueError("NoData cannot be filled with invented heights")
    a, b, c, d = values
    return (1-v)*((1-u)*a + u*b) + v*((1-u)*c + u*d)


def grid_triangles(side):
    """Godot clockwise front faces, row-major grid: +X east, +Z south."""
    for r in range(side - 1):
        for c in range(side - 1):
            k = r * side + c
            yield (k, k + 1, k + side)
            yield (k + 1, k + side + 1, k + side)


def clip_segment(a, b, bounds):
    """Liang-Barsky in X/Z; preserve intersections instead of joining across gaps."""
    xmin, zmin, xmax, zmax = bounds
    dx, dz = b[0] - a[0], b[1] - a[1]
    low, high = 0., 1.
    for p, q in [(-dx, a[0]-xmin), (dx, xmax-a[0]),
                 (-dz, a[1]-zmin), (dz, zmax-a[1])]:
        if abs(p) < 1e-12:
            if q < 0:
                return None
        elif p < 0:
            low = max(low, q / p)
        else:
            high = min(high, q / p)
    if low > high:
        return None
    return ([a[0]+low*dx, a[1]+low*dz], [a[0]+high*dx, a[1]+high*dz])


def lod_grid_error(heights, side, stride):
    """Exact max height difference between nested triangulated linear grids."""
    error = 0.
    for r in range(side):
        for c in range(side):
            i = min(r // stride * stride, side-1-stride)
            j = min(c // stride * stride, side-1-stride)
            v, u = (r-i)/stride, (c-j)/stride
            a, b = heights[i*side+j], heights[i*side+j+stride]
            d, e = heights[(i+stride)*side+j], heights[(i+stride)*side+j+stride]
            h = a+(b-a)*u+(d-a)*v if u+v <= 1 else e+(d-e)*(1-u)+(b-e)*(1-v)
            error = max(error, abs(h-heights[r*side+c]))
    return error
