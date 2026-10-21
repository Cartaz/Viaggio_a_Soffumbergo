"""Create local continuous construction references without changing terrain/OSM."""
import hashlib
import json
from pathlib import Path
from build_circuit_3d import encode, atomic_write
from coffa.loop_route import build
from coffa.loop_route import stationing, cut, join
from coffa.road_construction import road_footprint, SegmentIndex
from coffa.maneuver_search import search
import numpy as np


def planned_exits(result, points, config):
    p = np.asarray(points, dtype=float)
    station = stationing(p)
    t = np.diff(p[:, [0, 2]], axis=0)/np.diff(station)[:, None]
    angles = np.degrees(np.arccos(np.clip((t*np.roll(t, 1, axis=0)).sum(axis=1), -1, 1)))
    aprons = np.where((angles >= config['corner_apron_min_degrees']) &
                      (angles <= config['corner_apron_max_degrees']))[0]
    footprint = road_footprint(p, config['width_m'], aprons, config['corner_apron_radius_m'])
    footprint = footprint.simplify(config['footprint_simplify_m'], preserve_topology=True)
    index = SegmentIndex(p)
    replacements = {}
    for number in [0, 2]:
        turn = result['maneuvers'][number]
        a, b = turn['junction_before_station_m'], turn['junction_after_station_m']
        entry, exit_path = cut(p, station, a-12, a), cut(p, station, b, b+15)
        def pose(q, end=False):
            v = q[-1]-q[-2] if end else q[1]-q[0]
            body = q[-1] if end else q[0]
            v = v[[0, 2]]/np.linalg.norm(v[[0, 2]])
            rear = body[[0, 2]]-1.28*v
            return [*rear, np.arctan2(v[1], v[0])]
        primitives = search(footprint, pose(entry), pose(exit_path, True))
        groups = []
        previous = np.array(pose(entry))[None, :]
        for gear, arc in primitives:
            if not groups or groups[-1][0] != gear:
                groups.append([gear, previous.copy()])
            groups[-1][1] = np.vstack([groups[-1][1], arc])
            previous = arc[-1:]
        proposed = []
        for gear, states in groups:
            xz = states[:, :2]+1.28*np.column_stack([np.cos(states[:, 2]), np.sin(states[:, 2])])
            _, heights, _ = index.query(xz[:, 0], xz[:, 1], 4.26)
            if not np.isfinite(heights).all():
                raise ValueError('Planned maneuver outside known design profile')
            _, rh, _ = index.query(states[:, 0], states[:, 1], 4.26)
            proposed.append((gear, np.column_stack([xz[:, 0], heights, xz[:, 1]]),
                             np.column_stack([states[:, 0], rh, states[:, 1]])))

        def replace(leg):
            values = []
            def rear_reference(body):
                tangent = np.diff(body[:, [0, 2]], axis=0)
                tangent = np.vstack([tangent, tangent[-1]])
                tangent /= np.linalg.norm(tangent, axis=1)[:, None]
                rear = body.copy()
                rear[:, [0, 2]] -= 1.28*tangent
                return rear
            for n, (gear, q, rear) in enumerate(proposed):
                q = q.copy()
                if n == 0:
                    q[0] = entry[0]
                    prefix = cut(p, station, turn['buffer_start_station_m'], a-12)
                    q = join(prefix, q)
                    rear = np.vstack([rear_reference(prefix)[:-1], rear])
                local_length = float(stationing(q)[-1])
                if n == len(proposed)-1:
                    end = leg['source_station_range_m'][-1] if leg['source_station_range_m'] else b+50
                    tail = cut(p, station, b+15, end)
                    q = np.vstack([q, tail])
                    rear = np.vstack([rear, rear_reference(tail)])
                values.append({**leg, 'id':f'Raccordo M{number+1}.{n+1}', 'gear':gear,
                               'points_m':q.tolist(), 'length_horizontal_m':float(stationing(q)[-1]),
                               'geometric_proposal_only':True, 'rear_points_m':rear.tolist(),
                               'planned_local_length_m':local_length})
            return values
        replacements[2*number+2] = replace(result['legs'][2*number+2])
        fixture = result['maneuver_cases'][number]['legs']
        result['maneuver_cases'][number]['legs'] = fixture[:2]+replace(fixture[2])
    result['legs'] = [v for i, leg in enumerate(result['legs']) for v in replacements.get(i, [leg])]
    result['reference_length_m'] = sum(v['length_horizontal_m'] for v in result['legs'])
    result['local_exit_proposals'] = 'M1/M3 bicycle search on existing footprint, 0.10 m rectangle margin; Godot proof required'

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT/'build/circuit'
    path = folder/'construction_manifest.json'
    manifest = json.loads(path.read_bytes())
    config = json.loads((ROOT/'data/config/circuit_loop.json').read_bytes())
    result = build(manifest['engineering_construction']['profile_points_m'], config['reverse_beyond_junction_m'])
    if len(result['maneuvers']) != 4:
        raise ValueError('Expected four reviewed candidate reversals')
    planned_exits(result, manifest['engineering_construction']['profile_points_m'],
                  manifest['engineering_construction']['report']['config'])
    result.update({'schema_version':1, 'status':'construction_loop_with_backing_out_not_surveyed_maneuvers',
                   'construction_manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                   'config':config, 'original_candidate_modified':False, 'new_road_area_m2':0,
                   'real_maneuvers_verified':False, 'journey_including_visit_complete':False})
    atomic_write(folder/'loop.json', encode(result))
    print(json.dumps({k:v for k, v in result.items() if k not in ['legs', 'maneuver_cases', 'maneuvers']}, indent=2))


if __name__ == '__main__':
    main()
