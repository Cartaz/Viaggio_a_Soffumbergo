#!/usr/bin/env python3
"""Create a review-only OSM road-centerline candidate for circuit sector B.

Input: a georeferenced, continuous OSM GeoJSON road extract made by
`tools/fetch_geography.py --download`, NOT Google Maps screenshots.
Output: a candidate LineString with NO heights, road width or surveyed curves.
This tool never downloads data, guesses missing links or certifies drivable roads.
"""
import argparse
import heapq
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WAYPOINTS = ((13.3666683, 46.1271692),
             (13.3820732, 46.1331275),
             (13.3838913, 46.1345686))
ALLOWED_HIGHWAYS = {
    'secondary', 'tertiary', 'unclassified', 'residential',
    'living_street', 'service', 'track'
}


def haversine(a, b):
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    dl, dp = lon2 - lon1, lat2 - lat1
    z = math.sin(dp / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dl / 2) ** 2
    return 6371008.8 * 2 * math.asin(min(1, math.sqrt(z)))


def highway_graph(data):
    """Build geometry-only candidate graph: not a road legality or turn routing solver."""
    if data.get('type') != 'FeatureCollection':
        raise ValueError('Expected GeoJSON FeatureCollection')
    graph = {}
    for feature in data.get('features', []):
        properties = feature.get('properties', {})
        if (properties.get('highway') not in ALLOWED_HIGHWAYS or
                properties.get('access') in ('no', 'private') or
                properties.get('motor_vehicle') in ('no', 'private') or
                properties.get('motorcar') in ('no', 'private')):
            continue
        geometry = feature.get('geometry') or {}
        if geometry.get('type') != 'LineString':
            continue
        coords = geometry.get('coordinates', [])
        if len(coords) < 2 or any(len(p) != 2 for p in coords):
            raise ValueError('Road features need finite 2D WGS84 positions')
        coords = [tuple(p) for p in coords]
        if any(not all(math.isfinite(float(v)) for v in p) for p in coords):
            raise ValueError('Nonfinite road geometry')
        for a, b in zip(coords, coords[1:]):
            length = haversine(a, b)
            if length < 0.01:
                continue
            graph.setdefault(a, []).append((b, length))
            graph.setdefault(b, []).append((a, length))
    return graph


def nearest_node(graph, target, max_distance=60):
    if not graph:
        raise ValueError('No car-eligible roads in extract')
    found = min(graph, key=lambda p: haversine(target, p))
    distance = haversine(found, target)
    if distance > max_distance:
        raise ValueError(f'OSM extract incomplete: nearest anchor is {distance:.1f} m away')
    return found, distance


def shortest_path(graph, start, target):
    queue, best, parent = [(0.0, start)], {start: 0.0}, {}
    while queue:
        dist, u = heapq.heappop(queue)
        if dist > best[u] + 1e-6:
            continue
        if u == target:
            path = [u]
            while u != start:
                u = parent[u]
                path.append(u)
            return list(reversed(path)), dist
        for v, length in graph[u]:
            cost = dist + length
            if cost < best.get(v, math.inf):
                best[v], parent[v] = cost, u
                heapq.heappush(queue, (cost, v))
    raise ValueError('OSM network is disconnected between observation anchors')


def extract(data, max_snap_m=60):
    graph = highway_graph(data)
    snapped = [nearest_node(graph, p, max_snap_m) for p in WAYPOINTS]
    leg1, d1 = shortest_path(graph, snapped[0][0], snapped[1][0])
    leg2, d2 = shortest_path(graph, snapped[1][0], snapped[2][0])
    line = [list(p) for p in leg1 + leg2[1:]]
    # This is an OSM *candidate* even when the network is connected. Near a
    # junction, shortest-path selection may not reproduce the user's Google route.
    return {'type': 'FeatureCollection',
            'name': 'Sector_B_OSM_candidate_not_validated',
            'coordinate_reference_system': 'EPSG:4326; WGS84 longitude, latitude; no altitude',
            'license_notice': '© OpenStreetMap contributors; ODbL 1.0; https://www.openstreetmap.org/copyright',
            'route_status': 'candidate_only_requires_original_itinerary_and_panorama_review',
            'features': [{'type': 'Feature', 'id': 'B-OSM-CANDIDATE',
                          'geometry': {'type': 'LineString', 'coordinates': line},
                          'properties': {
                              'usable_as_road_mesh': False,
                              'length_osm_horizontal_m_approx': round(d1 + d2, 1),
                              'leg_lengths_m_approx': [round(d1, 1), round(d2, 1)],
                              'reference_app_rounded_m': [1800, 220],
                              'snap_distances_m': [round(item[1], 1) for item in snapped],
                              'unknowns': ['altitude', 'road_width', 'crossfall',
                                           'turn_restrictions', 'actual route choice',
                                           'visibility continuity', 'clearance', 'hairpin census']
                          }}]}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', required=True, type=Path,
                    help='complete OSM GeoJSON road extract; never Google linework')
    ap.add_argument('--output', required=True, type=Path,
                    help='output CANDIDATE file; requires manual verification')
    ap.add_argument('--max-snap-m', type=float, default=60)
    args = ap.parse_args()
    if args.max_snap_m <= 0 or not math.isfinite(args.max_snap_m):
        ap.error('Positive finite --max-snap-m required')
    candidate = extract(json.loads(args.input.read_text(encoding='utf-8')),
                        max_snap_m=args.max_snap_m)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + '\n',
                           encoding='utf-8')
    print('Only an OSM route *candidate* written; no drivable geometry certified.')


if __name__ == '__main__':
    main()