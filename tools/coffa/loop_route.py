"""A construction loop using explicit backing-out maneuvers on the unchanged axis.

At a retraced spur the car backs along its incoming path beyond the junction,
stops, then drives forward onto the outgoing branch. No rotation/teleport or
new road area is implied by this geometric reference; Jolt must prove execution.
"""
import numpy as np


def stationing(points):
    p = np.asarray(points, dtype=float)
    lengths = np.linalg.norm(np.diff(p[:, [0, 2]], axis=0), axis=1)
    if not np.isfinite(p).all() or np.any(lengths < 1e-6):
        raise ValueError('Invalid loop axis')
    return np.r_[0., np.cumsum(lengths)]


def cut(points, station, start, end):
    if not 0 <= start < end <= station[-1]:
        raise ValueError('Invalid source interval')
    def at(s):
        i = min(len(points)-2, max(0, np.searchsorted(station, s, side='right')-1))
        return points[i]+(points[i+1]-points[i])*(s-station[i])/(station[i+1]-station[i])
    return np.vstack([at(start), points[(station > start) & (station < end)], at(end)])


def maneuvers(points, buffer):
    p = np.asarray(points, dtype=float)
    station = stationing(p)
    if not np.isfinite(buffer) or buffer < 5 or buffer > 25:
        raise ValueError('Explicit backing buffer must be between 5 and 25 m')
    if not np.allclose(p[0], p[-1], atol=1e-6, rtol=0):
        raise ValueError('Expected a closed candidate')
    tangent = np.diff(p[:, [0, 2]], axis=0)/np.diff(station)[:, None]
    angle = np.degrees(np.arccos(np.clip((tangent*np.roll(tangent, 1, axis=0)).sum(axis=1), -1, 1)))
    result = []
    for r in np.where(angle > 179.99)[0]:
        n = 0
        while r-n-1 >= 0 and r+n+1 < len(p) and np.linalg.norm(p[r-n-1]-p[r+n+1]) < 1e-5:
            n += 1
        if n == 0 or station[r-n] < buffer:
            raise ValueError('Reversal lacks a confirmed retraced spur and incoming buffer')
        a, b = r-n, r+n
        result.append({'reversal_index':int(r), 'junction_before_index':int(a),
                       'junction_after_index':int(b), 'turn_station_m':float(station[r]),
                       'junction_before_station_m':float(station[a]),
                       'junction_after_station_m':float(station[b]),
                       'buffer_start_station_m':float(station[a]-buffer),
                       'spur_length_m':float(station[r]-station[a]),
                       'reference_point_m':p[r].tolist()})
    for first, second in zip(result, result[1:]):
        if first['junction_after_station_m'] >= second['buffer_start_station_m']:
            raise ValueError('Overlapping maneuver zones require manual review')
    return p, station, result


def join(a, b):
    if not np.allclose(a[-1], b[0], atol=1e-5, rtol=0):
        raise ValueError('Discontinuous construction reference')
    return np.vstack([a, b[1:]])


def build(points, buffer=15.):
    p, station, turns = maneuvers(points, buffer)
    legs, cases = [], []
    previous = None
    source_start = 0.

    def leg(values, gear, label, source_range):
        return {'id':label, 'gear':gear, 'sector':'construction_loop', 'points_m':values.tolist(),
                'length_horizontal_m':float(stationing(values)[-1]), 'source_station_range_m':source_range}

    for i, turn in enumerate(turns):
        r, a, b, start = (turn[k] for k in ['turn_station_m', 'junction_before_station_m',
                                           'junction_after_station_m', 'buffer_start_station_m'])
        forward = cut(p, station, source_start, r)
        if previous is not None:
            forward = join(cut(p, station, previous['buffer_start_station_m'], previous['junction_before_station_m']), forward)
        legs.append(leg(forward, 1, f'Avanti {i+1}', [source_start, r]))
        reverse = cut(p, station, start, r)[::-1]
        legs.append(leg(reverse, -1, f'Retro {i+1}', [r, b]))
        # Small independent fixture for each maneuver, on identical source geometry.
        entry = cut(p, station, max(0, a-25), r)
        exit_path = join(cut(p, station, start, a), cut(p, station, b, min(station[-1], b+50)))
        cases.append({'id':f'M{i+1}', 'maneuver':turn, 'legs':[
            leg(entry, 1, 'Ingresso', []), leg(reverse, -1, 'Retromarcia', []), leg(exit_path, 1, 'Uscita', [])]})
        source_start, previous = b, turn
    final = cut(p, station, source_start, station[-1])
    if previous is not None:
        final = join(cut(p, station, previous['buffer_start_station_m'], previous['junction_before_station_m']), final)
    legs.append(leg(final, 1, 'Rientro', [source_start, float(station[-1])]))
    for left, right in zip(legs, legs[1:]):
        if not np.allclose(left['points_m'][-1], right['points_m'][0], atol=1e-5, rtol=0):
            raise ValueError('Discontinuous phase boundary')
    return {'legs':legs, 'maneuver_cases':cases, 'maneuvers':turns,
            'source_length_m':float(station[-1]),
            'reference_length_m':sum(v['length_horizontal_m'] for v in legs),
            'extra_backtrack_m':2*buffer*len(turns)}
