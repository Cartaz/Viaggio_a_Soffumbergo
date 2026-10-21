"""Local bicycle search inside an existing design footprint, not new road geometry.

Coordinates are a rear axle position plus planar body heading. Search checks the
whole 1.745 x 3.94 m vehicle rectangle, at 0.125 m intervals. Godot execution is
still required; this is a geometric proposal, not surveyed maneuver clearance.
"""
import heapq
import math
import numpy as np
import shapely


def search(footprint, start, goal, max_nodes=250000, step_m=1., grid_m=.35, min_run=3):
    footprint = footprint.buffer(-.10)
    shapely.prepare(footprint)
    start, goal = np.asarray(start, dtype=float), np.asarray(goal, dtype=float)
    reference = start[:2].copy()
    def angle(a):
        return (a+math.pi) % (2*math.pi)-math.pi
    def key(p, gear, run=min_run):
        return (round((p[0]-reference[0])/grid_m), round((p[1]-reference[1])/grid_m),
                round(angle(p[2])/math.radians(5)), gear, min(min_run, run))
    def safe(states):
        c, s = np.cos(states[:, 2]), np.sin(states[:, 2])
        corners = np.array([[-.69, -.8725], [3.25, -.8725], [3.25, .8725], [-.69, .8725]])
        x = states[:, 0, None]+c[:, None]*corners[:, 0]-s[:, None]*corners[:, 1]
        y = states[:, 1, None]+s[:, None]*corners[:, 0]+c[:, None]*corners[:, 1]
        polygons = shapely.polygons(np.stack([x, y], axis=-1))
        return bool(shapely.covers(footprint, polygons).all())
    def heuristic(p):
        return np.linalg.norm(p[:2]-goal[:2])+2*abs(angle(p[2]-goal[2]))
    # Each record retains its immutable parent; a cheaper replacement never rewires children.
    records = [(start, 1, 0., -1, 0., None, min_run)]
    queue = [(heuristic(start), 0)]
    best = {key(start, 1): 0.}
    step = np.linspace(step_m/8, step_m, 8)
    for _ in range(max_nodes):
        if not queue:
            break
        _, idx = heapq.heappop(queue)
        p, old_gear, cost, parent, old_k, _arc, run = records[idx]
        if cost > best.get(key(p, old_gear, run), math.inf)+1e-8:
            continue
        if np.linalg.norm(p[:2]-goal[:2]) < .65 and abs(angle(p[2]-goal[2])) < math.radians(7):
            path = []
            while idx >= 0:
                rec = records[idx]
                if rec[5] is not None:
                    path.append((rec[1], rec[5]))
                idx = rec[3]
            return list(reversed(path))
        for gear in [1, -1]:
            if gear != old_gear and run < min_run:
                continue
            for curvature in [-.18, -.09, 0., .09, .18]:
                d = gear*step
                heading = p[2]+curvature*d
                if curvature:
                    x = p[0]+(np.sin(heading)-math.sin(p[2]))/curvature
                    y = p[1]-(np.cos(heading)-math.cos(p[2]))/curvature
                else:
                    x, y = p[0]+d*math.cos(p[2]), p[1]+d*math.sin(p[2])
                states = np.column_stack([x, y, heading])
                end = states[-1]
                new_cost = cost+step_m+(3. if gear != old_gear else 0)+abs(curvature-old_k)
                new_run = run+1 if gear == old_gear else 1
                k = key(end, gear, new_run)
                if new_cost >= best.get(k, math.inf) or not safe(states):
                    continue
                best[k] = new_cost
                records.append((end, gear, new_cost, idx, curvature, states, new_run))
                heapq.heappush(queue, (new_cost+heuristic(end), len(records)-1))
    raise ValueError('No bounded maneuver found inside existing surface')
