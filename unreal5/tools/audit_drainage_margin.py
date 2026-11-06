"""Sample the existing asphalt-to-curb margin before designing drainage.

No excavation, replacement surface, inferred metric photo measurement or engine
acceptance is produced. Heights are existing generated triangles and native R16.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import shapely

from prepare_reentry_checks import NativeGround
from road_surface import RoadSurface

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--review', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError('Preserve the previous margin audit')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    review = json.loads(args.review.read_text(encoding='utf-8'))
    assert review['geometry_build_id'] == manifest['build_id']
    curb = next(r for r in manifest['rockfall_edges']['records'] if r['kind'] == 'rockfall_curb')
    payload = json.loads(Path(curb['source']).read_text())
    solids = (np.asarray(payload['vertices_cm']) + curb['location_cm']).reshape(-1, 8, 3) / 100
    tile = next(t for t in manifest['tiles'] if t['id'] == curb['tile'])
    paths = [args.manifest, args.review, Path(__file__), ROOT/'tools/road_surface.py',
             ROOT/'tools/prepare_reentry_checks.py', ROOT/'terrain/world_tiles/manifest.json',
             Path(curb['source']), Path(tile['heightmap']), Path(tile['holes'])]
    paths += [Path(m['source']) for m in manifest['meshes'] if m['kind'] in ['asphalt', 'shoulder']]
    guards = {str(p.resolve()): sha(p) for p in paths}
    assert sha(curb['source']) == curb['sha256']
    assert sha(tile['heightmap']) == tile['height_sha256'] and sha(tile['holes']) == tile['holes_sha256']
    for m in manifest['meshes']:
        if m['kind'] in ['asphalt', 'shoulder']:
            assert sha(m['source']) == m['sha256']
    road = RoadSurface(manifest)
    shoulder = RoadSurface(manifest, include_shoulders=True)
    ground = NativeGround(manifest)
    bounds = np.r_[solids[:, :, :2].min(axis=(0, 1))-5, solids[:, :, :2].max(axis=(0, 1))+5] * 100
    ids = road.tree.query(shapely.box(*bounds), predicate='intersects')
    footprint = shapely.transform(shapely.union_all(road.polygons[ids]), lambda p: p/100)
    assert not footprint.is_empty
    samples = []
    for index, solid in enumerate(solids):
        # joined_prism stores the inner face as corners 0/1 and 4/5.
        length = np.linalg.norm(solid[1, :2]-solid[0, :2])
        steps = max(1, int(np.ceil(length/.1)))
        for t in np.linspace(0, 1, steps+1):
            inner = solid[0, :2]*(1-t)+solid[1, :2]*t
            line = shapely.shortest_line(shapely.Point(inner), footprint)
            edge = np.asarray(shapely.get_point(line, -1).coords)[0]
            width = float(np.linalg.norm(inner-edge))
            if width <= 1.e-6:
                raise RuntimeError('Existing curb overlaps asphalt; no free margin')
            samples.append((index, float(t), inner, edge, width))
    inner = np.asarray([r[2] for r in samples]);edges = np.asarray([r[3] for r in samples])
    fractions = np.linspace(.05, .95, 10)
    xy = edges[:, None] + (inner-edges)[:, None]*fractions[None, :, None]
    asphalt_z, distance = road.sample(edges*100)
    assert distance.max() < .01
    asphalt_z /= 100
    native = ground.sample(xy.reshape(-1, 2)).reshape(len(samples), -1)
    shoulder_z, shoulder_distance = shoulder.sample(xy.reshape(-1, 2)*100)
    shoulder_z = shoulder_z.reshape(native.shape)/100
    on_shoulder = shoulder_distance.reshape(native.shape) < .01
    support = np.maximum(native, np.where(on_shoulder, shoulder_z, -np.inf))
    assert np.isfinite(native).all() and np.isfinite(support).all()
    relative = support-asphalt_z[:, None]
    widths = np.asarray([r[4] for r in samples])
    args.output.mkdir(parents=True)
    with (args.output/'cross_sections.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['curb_segment', 'segment_fraction', 'gap_width_m', 'gap_fraction',
                         'UE_x_m', 'UE_y_m', 'asphalt_edge_z_m', 'native_z_m',
                         'on_road_or_shoulder', 'existing_visible_support_z_m', 'support_minus_asphalt_m'])
        for i, row in enumerate(samples):
            for j, fraction in enumerate(fractions):
                writer.writerow([row[0], row[1], row[4], fraction, *xy[i, j], asphalt_z[i],
                                 native[i, j], bool(on_shoulder[i, j]), support[i, j], relative[i, j]])
    unchanged = all(sha(path) == expected for path, expected in guards.items())
    report = {
        'build_id': manifest['build_id'], 'recorded_unix': time.time(),
        'audit_completed': True, 'source_inputs_unchanged': unchanged,
        'curb_solids': len(solids), 'cross_sections': len(samples), 'margin_probes': int(native.size),
        'sampling_step_along_each_curb_segment_at_most_m': .1,
        'fractional_width_samples': fractions.tolist(),
        'existing_gap_width_min_m': float(widths.min()), 'existing_gap_width_max_m': float(widths.max()),
        'existing_support_minus_asphalt_min_m': float(relative.min()),
        'existing_support_minus_asphalt_max_m': float(relative.max()),
        'existing_support_at_or_above_asphalt_probe_count': int(np.count_nonzero(relative >= 0)),
        'road_or_shoulder_coverage_probe_count': int(on_shoulder.sum()),
        'protected_input_sha256': guards,
        'cross_sections_sha256': sha(args.output/'cross_sections.csv'),
        'metric_photo_measurements': False, 'new_geometry_created': False,
        'terrain_or_asphalt_modified': False, 'native_engine_executed': False,
        'drainage_geometry_accepted': False,
        'method': 'Shortest planimetric segment from each existing curb inner face to exact local asphalt footprint. '
                  'Ten probes across its interior; top support is maximum of native R16 triangle and covering existing road/shoulder triangle.',
        'limitations': 'Finite CPU samples of existing engineered geometry, not continuous extrema, hydraulic capacity, '
                       'a native collision test, a measured ditch section or a rendering acceptance. '
                       'Use this to constrain a separate versioned drainage design; photographs do not resolve metric depth or width.',
    }
    (args.output/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'protected_input_sha256'}, indent=2))
    if not unchanged:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
