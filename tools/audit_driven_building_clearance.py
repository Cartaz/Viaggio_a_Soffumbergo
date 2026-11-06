"""Compare sampled native chassis poses with approximate mapped footprints.

This is a source-layout diagnostic, not a native collision test or a claim that
an OSM boundary/height is surveyed. Positive overlap requires source review.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import time

import numpy as np
from pyproj import Transformer
import shapely
from run_guardrail_check import rotate

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--draft', type=Path, required=True); parser.add_argument('--lap-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    if args.output.exists(): raise RuntimeError('Preserve previous clearance diagnostic')
    draft = args.draft.resolve(); lap_path = args.lap_report.resolve(); lap = read(lap_path)
    pack = read(draft/'candidate_packaging_report.json'); identity = read(draft/'native_runtime_identity.json')
    assert lap['full_lap_passed'] and lap['packaged'] and not lap['rendering']
    assert lap['build_id'] == pack['build_id'] == identity['build_id']
    assert lap['runtime_binary_sha256'] == pack['game_binary_sha256']
    manifest = Path(read(draft/'import_report.json')['manifest']); m = read(manifest)
    assert lap['runtime_world_sha256'] == sha(draft/'circuit_driving_world.json') == pack['world_sha256']
    native = ROOT/'Unreal/Source/SoffumbergoLab/LabVehicle.cpp'
    assert sha(native) == identity['source_sha256'][str(native)]
    text = native.read_text(encoding='utf-8')
    assert re.search(r'Chassis\.X=380;\s*Chassis\.Y=168;\s*Chassis\.Z=75;', text)
    assert 'FVector(0,0,70))*RootReference.Inverse()' in text
    assert all(sha(p) == value for p, value in identity['source_sha256'].items())
    telemetry = lap_path.parent/(lap_path.parent.name+'.csv')
    source = ROOT/'data/geography/world_cover_20261024_buildings_v4'
    provenance = read(source/'provenance.json')
    assert sha(source/'cover.geojson') == provenance['geojson_sha256']
    assert sha(source/'response.json') == provenance['response_sha256']
    paths = [manifest, lap_path, telemetry, native, ROOT/'tools/run_guardrail_check.py', Path(__file__),
        source/'cover.geojson', source/'response.json', source/'provenance.json', draft/'native_runtime_identity.json']
    before = {str(p): sha(p) for p in paths}
    with telemetry.open(encoding='utf-8-sig') as stream:
        rows = np.asarray([[float(row[k]) for k in ['time_s','x_m','y_m','z_m','qw','qx','qy','qz']]
                           for row in csv.DictReader(stream)])
    elapsed = rows[:, 0]; xyz = rows[:, 1:4]*[1, -1, 1]; quaternion = rows[:, 4:8]
    assert len(rows) > 0 and np.isfinite(rows).all() and np.all(np.diff(elapsed) > 0)
    assert np.max(np.abs(np.linalg.norm(quaternion, axis=1)-1)) < 1.e-6
    corners = np.asarray([[x, y, z] for x in [-1.9, 1.9] for y in [-.84, .84] for z in [.325, 1.075]])
    body = rotate(quaternion, corners)+xyz[:, None]
    chassis = shapely.convex_hull(shapely.multipoints(body[:, :, :2]))
    features = read(source/'cover.geojson')['features']; raw = read(source/'response.json')
    relations = {int(f['id'].split('/')[1]) for f in features if f['id'].startswith('relation/')}
    members = {member['ref'] for row in raw['elements'] if row['type'] == 'relation' and row['id'] in relations
               for member in row.get('members', []) if member['type'] == 'way' and member.get('role', '') in ['', 'outer', 'inner']}
    projection = Transformer.from_crs(4326, 6708, always_xy=True, allow_ballpark=False)
    inverse = Transformer.from_crs(6708, 4326, always_xy=True, allow_ballpark=False)
    origin = np.asarray(m['origin_ENH_m']); buildings = []; ids = []; rejected = []
    for feature in features:
        if feature['id'].startswith('way/') and int(feature['id'].split('/')[1]) in members: continue
        geometry = shapely.from_geojson(json.dumps(feature['geometry']))
        if geometry.geom_type == 'LineString' and geometry.is_closed: geometry = shapely.Polygon(geometry.coords)
        geometry = shapely.transform(geometry, projection.transform, interleaved=False)
        geometry = shapely.transform(geometry, lambda p: np.c_[p[:, 0]-origin[0], origin[1]-p[:, 1]])
        if not geometry.is_valid: geometry = shapely.make_valid(geometry)
        if geometry.geom_type not in ['Polygon', 'MultiPolygon'] or geometry.is_empty:
            rejected.append(feature['id']); continue
        buildings.append(geometry); ids.append(feature['id'])
    buildings = np.asarray(buildings, dtype=object)
    pairs = shapely.STRtree(buildings).query(chassis, predicate='intersects')
    area = shapely.area(shapely.intersection(chassis[pairs[0]], buildings[pairs[1]]))
    positive = area > 1.e-8; pairs = pairs[:, positive]; area = area[positive]
    args.output.mkdir(parents=True)
    csv_path = args.output/'sampled_plan_overlaps.csv'
    with csv_path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream); writer.writerow(['sample_index','time_s','source_id','overlap_area_m2','vehicle_UE_x_m','vehicle_UE_y_m'])
        for a, b, size in zip(*pairs, area): writer.writerow([a, elapsed[a], ids[b], size, *xyz[a, :2]])
    cases = []
    for index in np.unique(pairs[1]):
        positions = np.flatnonzero(pairs[1] == index); samples = np.unique(pairs[0, positions]); peak = positions[np.argmax(area[positions])]
        sample = pairs[0, peak]; lon, lat = inverse.transform(xyz[sample, 0]+origin[0], origin[1]-xyz[sample, 1])
        splits = np.split(samples, np.flatnonzero(np.diff(samples) > 1)+1)
        cases.append({'source_id': ids[index], 'overlapping_pose_samples': len(samples),
            'samples_after_initial_two_seconds': int(np.count_nonzero(elapsed[samples] > 2)),
            'maximum_sampled_plan_overlap_m2': float(area[peak]), 'first_time_s': float(elapsed[samples[0]]),
            'last_time_s': float(elapsed[samples[-1]]), 'peak_time_s': float(elapsed[sample]),
            'vehicle_at_peak_wgs84': [lat, lon], 'sample_intervals': [[float(elapsed[g[0]]), float(elapsed[g[-1]])] for g in splits],
            'real_collision_confirmed': False, 'source_alignment_review_required': True})
    cases.sort(key=lambda row: -row['maximum_sampled_plan_overlap_m2'])
    unchanged = all(sha(p) == expected for p, expected in before.items())
    report = {'build_id': m['build_id'], 'recorded_unix': time.time(), 'diagnostic_completed': True,
        'native_full_lap_report': str(lap_path), 'windows_binary_sha256': pack['game_binary_sha256'],
        'pose_samples_checked': len(rows), 'mapped_buildings_checked': len(buildings), 'unusable_geometries': rejected,
        'chassis_dimensions_m': [3.8, 1.68, .75], 'chassis_center_local_m': [0, 0, .7],
        'quaternion_method': 'Same native reflected-Y conversion and eight-corner projection used by the physical guardrail verifier.',
        'positive_area_numerical_epsilon_m2': 1.e-8, 'pose_samples_with_mapped_overlap': len(np.unique(pairs[0])),
        'mapped_buildings_with_overlap': len(cases), 'cases': cases,
        'protected_input_sha256': before, 'source_inputs_unchanged': unchanged, 'overlap_csv_sha256': sha(csv_path),
        'new_collision_or_geometry_created': False, 'real_building_collisions_proven': False,
        'scope': 'Finite sampled horizontal projections of the actual physics chassis against approximate mapped building footprints. '
                 'Not a continuous swept test, facade/height measurement or real-world collision verdict. '
                 'Vertical separation, arcades, mapping errors and actual sidewalk/road relationships require Street View. '
                 'Roof/coffa/occupant visual extents are not included. Native road-only lap success does not settle these source-layout conflicts.'}
    (args.output/'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k not in ['cases', 'protected_input_sha256']}, indent=2))
    print(json.dumps({'highest_priority_cases': cases[:5]}, indent=2))
    if not unchanged: raise SystemExit(1)


if __name__ == '__main__': main()
