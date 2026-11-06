"""Inventory mapped roadside buildings for source review; never invent models."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pyproj
import shapely
from prepare_reentry_checks import NativeGround
from road_surface import RoadSurface

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--draft', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--corridor-m', type=float, default=30)
    args = parser.parse_args(); draft = args.draft.resolve()
    if args.output.exists(): raise RuntimeError('Preserve previous building review inventory')
    if not np.isfinite(args.corridor_m) or not 0 < args.corridor_m <= 1000: raise ValueError('Invalid review corridor')
    imported = json.loads((draft/'import_report.json').read_text()); assert imported['all_imported']
    manifest = Path(imported['manifest']); m = json.loads(manifest.read_text())
    folder = ROOT/'data/geography/world_cover_20261024_buildings_v4'
    provenance = json.loads((folder/'provenance.json').read_text())
    assert sha(folder/'cover.geojson') == provenance['geojson_sha256']
    assert sha(folder/'response.json') == provenance['response_sha256']
    collection = json.loads((folder/'cover.geojson').read_text()); raw = json.loads((folder/'response.json').read_text())
    relations = {int(f['id'].split('/')[1]) for f in collection['features'] if f['id'].startswith('relation/')}
    members = {member['ref'] for row in raw['elements'] if row['type'] == 'relation' and row['id'] in relations
               for member in row.get('members', []) if member['type'] == 'way' and member.get('role', '') in ['', 'outer', 'inner']}
    paths = [manifest, draft/'circuit_itinerary.json', folder/'provenance.json', folder/'response.json',
             folder/'cover.geojson', Path(__file__), ROOT/'tools/road_surface.py', ROOT/'tools/prepare_reentry_checks.py']
    paths += [Path(t[key]) for t in m['tiles'] for key in ['heightmap', 'holes']]
    paths += [Path(r['source']) for r in m['meshes'] if r['kind'] == 'asphalt']
    before = {str(p.resolve()): sha(p) for p in paths}
    pyproj.network.set_network_enabled(False)
    project = pyproj.Transformer.from_crs(4326, 6708, always_xy=True, allow_ballpark=False)
    inverse = pyproj.Transformer.from_crs(6708, 4326, always_xy=True, allow_ballpark=False)
    origin = np.asarray(m['origin_ENH_m'])
    itinerary = json.loads((draft/'circuit_itinerary.json').read_text()); assert itinerary['build_id'] == m['build_id']
    route = shapely.LineString(np.asarray(itinerary['points_cm'])[:, :2]/100)
    road = RoadSurface(m); ground = NativeGround(m)
    features = []; polygons = []; rejected = []; deduplicated = 0
    for feature in collection['features']:
        if feature['id'].startswith('way/') and int(feature['id'].split('/')[1]) in members:
            deduplicated += 1; continue
        geometry = shapely.from_geojson(json.dumps(feature['geometry']))
        if geometry.geom_type == 'LineString' and geometry.is_closed: geometry = shapely.Polygon(geometry.coords)
        geometry = shapely.transform(geometry, project.transform, interleaved=False)
        geometry = shapely.transform(geometry, lambda p: np.c_[p[:, 0]-origin[0], origin[1]-p[:, 1]])
        if not geometry.is_valid: geometry = shapely.make_valid(geometry)
        if geometry.geom_type not in ['Polygon', 'MultiPolygon'] or geometry.is_empty or geometry.area <= 0:
            rejected.append({'id': feature['id'], 'reason': 'No usable polygon after source validation'}); continue
        features.append(feature); polygons.append(geometry)
    centimeters = shapely.transform(np.asarray(polygons, dtype=object), lambda p: p*100)
    pairs, distances = road.tree.query_nearest(centimeters, all_matches=False, return_distance=True)
    distance = np.empty(len(polygons)); distance[pairs[0]] = distances/100
    selected = np.flatnonzero(distance <= args.corridor_m)
    rows = []; source_features = []
    for index in selected:
        geometry = polygons[index]; feature = features[index]; point = geometry.representative_point()
        station = float(route.project(point)); view = route.interpolate(station)
        longitude, latitude = inverse.transform(point.x+origin[0], origin[1]-point.y)
        view_lon, view_lat = inverse.transform(view.x+origin[0], origin[1]-view.y)
        heading = float(np.degrees(np.arctan2(point.x-view.x, view.y-point.y)) % 360)
        ids = road.tree.query(centimeters[index], predicate='intersects')
        overlap = float(shapely.area(shapely.intersection(centimeters[index], shapely.union_all(road.polygons[ids])))/10000) if len(ids) else 0.0
        parts = list(geometry.geoms) if geometry.geom_type == 'MultiPolygon' else [geometry]
        samples = []
        for part in parts:
            coordinates = np.asarray(part.exterior.coords)
            samples.extend(coordinates.tolist()); samples.extend(((coordinates[:-1]+coordinates[1:])/2).tolist())
        samples.append([point.x, point.y]); heights = ground.sample(np.asarray(samples)); valid = heights[np.isfinite(heights)]
        row = {'source_id': feature['id'], 'source_tags': feature['properties'],
            'mapped_footprint_area_m2': float(geometry.area), 'minimum_generated_asphalt_distance_m': float(distance[index]),
            'mapped_footprint_asphalt_overlap_m2': overlap, 'first_nearest_route_station_m': station,
            'representative_wgs84': [latitude, longitude], 'representative_UE_xy_m': [point.x, point.y],
            'native_ground_samples': len(heights), 'native_ground_missing_samples': int(np.count_nonzero(~np.isfinite(heights))),
            'current_native_ground_min_local_m': float(valid.min()) if len(valid) else None,
            'current_native_ground_max_local_m': float(valid.max()) if len(valid) else None,
            'streetview_candidate_url': f'https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={view_lat:.9f},{view_lon:.9f}&heading={heading:.3f}&pitch=0&fov=80',
            'streetview_review_complete': False, 'height_or_floors_verified': False, 'native_building_created': False,
            'priority': 'Resolve possible footprint/alignment conflict in Street View' if overlap > 0 else 'Review visible facade, entrances, roof and roadside relationship'}
        rows.append(row); source_features.append(feature)
    rows.sort(key=lambda r: (-int(r['mapped_footprint_asphalt_overlap_m2'] > 0), r['minimum_generated_asphalt_distance_m'], r['first_nearest_route_station_m']))
    args.output.mkdir(parents=True)
    (args.output/'mapped_buildings_wgs84.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': source_features}))
    unchanged = all(sha(p) == expected for p, expected in before.items())
    report = {'build_id': m['build_id'], 'recorded_unix': time.time(), 'inventory_complete': True,
        'source_feature_count': len(collection['features']), 'relation_member_ways_deduplicated': deduplicated,
        'unusable_source_geometries': rejected, 'usable_mapped_buildings': len(features), 'corridor_m': args.corridor_m,
        'selected_buildings': len(rows), 'mapped_footprint_asphalt_overlaps': sum(r['mapped_footprint_asphalt_overlap_m2'] > 0 for r in rows),
        'current_manifest_building_mesh_records': sum(r['kind'] == 'building' for r in m['meshes']),
        'projection_description': project.description, 'projection_declared_accuracy_m': project.accuracy,
        'origin_ENH_m': origin.tolist(), 'protected_input_sha256': before, 'source_inputs_unchanged': unchanged,
        'attribution': 'OpenStreetMap contributors, ODbL-1.0', 'attribution_url': 'https://www.openstreetmap.org/copyright',
        'buildings': rows, 'new_models_created': False, 'native_engine_executed': False,
        'scope': 'Source review queue from approximate mapped footprints near existing generated asphalt. '
                 'OSM heights/floors are unverified tags, native samples are current engineered ground rather than roofs. '
                 'Overlap is a mapping/alignment review flag, not proof that a real house intersects the road. '
                 'Station is the first closest occurrence on possibly repeated route segments. '
                 'No uniform blockouts, inferred facades, new terrain or construction dimensions accepted.'}
    (args.output/'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k not in ['buildings', 'protected_input_sha256']}, indent=2))
    if not unchanged: raise SystemExit(1)


if __name__ == '__main__': main()
