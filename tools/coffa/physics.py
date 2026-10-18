"""Rigid aggregate, diagnostic stability and passive wheel-force kernels.

These are design tools, not a claim of validated Toyota dynamics.
"""
import math


def _finite(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError("Expected a finite number")
    return float(value)


def aggregate(components):
    """Full tensor about COM; aligned solid-box local inertias + parallel axes."""
    ids = set()
    parts = []
    for item in components:
        if item["id"] in ids:
            raise ValueError("Duplicate component: " + item["id"])
        ids.add(item["id"])
        mass = _finite(item["mass_kg"])
        p = tuple(map(_finite, item["position_m"]))
        size = tuple(map(_finite, item["box_m"]))
        if mass <= 0 or len(p) != 3 or len(size) != 3 or min(size) <= 0:
            raise ValueError("Invalid mass, position or box")
        parts.append((mass, p, size))
    if not parts:
        raise ValueError("Empty assembly")
    mass = sum(x[0] for x in parts)
    com = [sum(m * p[i] for m, p, _ in parts) / mass for i in range(3)]
    tensor = [[0.0] * 3 for _ in range(3)]
    for m, p, size in parts:
        r = [p[i] - com[i] for i in range(3)]
        rr = sum(v * v for v in r)
        for i in range(3):
            for j in range(3):
                tensor[i][j] += m * ((rr if i == j else 0) - r[i] * r[j])
            tensor[i][i] += m * sum(size[j] ** 2 for j in range(3) if i != j) / 12
    return {"mass_kg": mass, "com_m": com, "inertia_kg_m2": tensor}


def stability(track, com):
    """Rigid flat-road diagnostics only. Not a rollover event or dynamic predictor."""
    track = _finite(track)
    x, y, _ = map(_finite, com)
    if track <= 0 or y <= 0 or abs(x) >= track / 2:
        raise ValueError("COM must be above and within track")
    margin = track / 2 - abs(x)
    return {"ssf_centered": track / (2 * y), "weak_side_a_over_g": margin / y,
            "weak_side_static_tilt_deg": math.degrees(math.atan2(margin, y))}


def friction_circle(longitudinal, lateral, normal_load, mu):
    values = list(map(_finite, (longitudinal, lateral, normal_load, mu)))
    longitudinal, lateral, normal_load, mu = values
    if normal_load < 0 or mu < 0:
        raise ValueError("Negative normal load or friction")
    requested = math.hypot(longitudinal, lateral)
    scale = min(1.0, mu * normal_load / requested) if requested else 1.0
    return longitudinal * scale, lateral * scale


def suspension(compression, compression_speed, spring, damping, bump_compression=None,
               bump_spring=0.0):
    """Compression speed positive on compression. No tensile contact force."""
    if min(spring, damping, bump_spring) < 0:
        raise ValueError("Passive coefficients must be nonnegative")
    extra = max(0.0, compression - bump_compression) if bump_compression is not None else 0.0
    return max(0.0, spring * compression + damping * compression_speed + bump_spring * extra)


def reachable(distance, upper, lower, tolerance=1e-9):
    """Fixed two-link chain: no stretch allowed, including inner unreachable region."""
    if min(distance, upper, lower) < 0:
        raise ValueError("Negative length")
    return abs(upper - lower) - tolerance <= distance <= upper + lower + tolerance
