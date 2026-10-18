"""Small WGS84/ECEF/ENU pipeline. No projection packages, no invented elevation."""
import math

A = 6378137.0
E2 = 6.6943799901413165e-3


def _coordinate(c):
    if len(c) != 3 or any(not math.isfinite(x) for x in c):
        raise ValueError("A finite [longitude, latitude, ellipsoidal_height] is required")
    lon, lat, h = c
    if abs(lon) > 180 or abs(lat) > 90:
        raise ValueError("Coordinate outside WGS84 bounds")
    return lon, lat, h


def ecef(coordinate):
    lon, lat, h = _coordinate(coordinate)
    lon, lat = math.radians(lon), math.radians(lat)
    n = A / math.sqrt(1 - E2 * math.sin(lat) ** 2)
    return ((n + h) * math.cos(lat) * math.cos(lon),
            (n + h) * math.cos(lat) * math.sin(lon),
            (n * (1 - E2) + h) * math.sin(lat))


def to_godot(coordinate, origin):
    """ECEF -> local ENU -> Godot east/up/south. Heights must share datum."""
    lon, lat, _ = _coordinate(origin)
    lon, lat = math.radians(lon), math.radians(lat)
    d = [p - q for p, q in zip(ecef(coordinate), ecef(origin))]
    east = -math.sin(lon) * d[0] + math.cos(lon) * d[1]
    north = -math.sin(lat) * math.cos(lon) * d[0] - math.sin(lat) * math.sin(lon) * d[1] + math.cos(lat) * d[2]
    up = math.cos(lat) * math.cos(lon) * d[0] + math.cos(lat) * math.sin(lon) * d[1] + math.sin(lat) * d[2]
    return [east, up, -north]


def resample(points, max_step=3.0):
    """Piecewise linear densification retains every surveyed corner, including close hairpins."""
    if len(points) < 2 or not math.isfinite(max_step) or max_step <= 0:
        raise ValueError("Need at least two points and positive step")
    if any(len(p) != 3 or any(not math.isfinite(x) for x in p) for p in points):
        raise ValueError("Invalid point")
    result = [list(points[0])]
    for p, q in zip(points, points[1:]):
        distance = math.dist(p, q)
        if distance < 1e-8:
            continue
        count = math.ceil(distance / max_step)
        for i in range(1, count + 1):
            fraction = i / count
            result.append([p[j] + (q[j] - p[j]) * fraction for j in range(3)])
    if len(result) < 2:
        raise ValueError("Degenerate route")
    return result


def radius_horizontal(a, b, c):
    """Circumcircle of x/z coordinates. Local diagnostic, not a speed limit."""
    ab = math.hypot(a[0] - b[0], a[2] - b[2])
    bc = math.hypot(b[0] - c[0], b[2] - c[2])
    ca = math.hypot(c[0] - a[0], c[2] - a[2])
    twice_area = abs((b[0] - a[0]) * (c[2] - a[2]) - (b[2] - a[2]) * (c[0] - a[0]))
    return ab * bc * ca / (2 * twice_area) if twice_area > 1e-10 else None


def road_strip(points, width):
    """Flat camber test mesh; vertical grade preserved, crossfall explicitly unknown.

    Hairpin joins are bevel-free centre-tangent approximations, for blockout only.
    Final road requires surveyed widths/crossfall and junction meshing.
    """
    if not math.isfinite(width) or width <= 0:
        raise ValueError("Positive width required")
    vertices, triangles = [], []
    for i, p in enumerate(points):
        before, after = points[max(0, i - 1)], points[min(len(points) - 1, i + 1)]
        dx, dz = after[0] - before[0], after[2] - before[2]
        n = math.hypot(dx, dz)
        if n < 1e-8:
            raise ValueError("Vertical path or folded duplicate requires manual cleanup")
        # forward cross UP = (-dz, 0, dx).
        rx, rz = -dz / n * width / 2, dx / n * width / 2
        vertices.extend([[p[0] - rx, p[1], p[2] - rz], [p[0] + rx, p[1], p[2] + rz]])
        if i:
            k = 2 * i
            # Clockwise winding when viewed from above (Godot front face).
            triangles.extend([[k - 2, k, k - 1], [k - 1, k, k + 1]])
    return vertices, triangles
