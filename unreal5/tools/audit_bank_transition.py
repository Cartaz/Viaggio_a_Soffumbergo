"""Independent saved-data scope, clearance and continuity audit of a bank refit."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import shapely
from prepare_reentry_checks import NativeGround
from road_surface import RoadSurface

ROOT = Path(__file__).resolve().parents[1]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(); p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); args = p.parse_args()
    if args.output.exists(): raise RuntimeError('Preserve earlier audit')
    m = json.loads(args.manifest.read_text()); change = m['bank_transition']; cfg = change['config']
    old = json.loads(Path(change['parent_manifest']).read_text()); base = json.loads((ROOT/'terrain/world_tiles/manifest.json').read_text())
    records = {r['id']: r for r in change['records']}; before = {r['id']: r for r in old['meshes']}
    after = {r['id']: r for r in m['meshes']}; tiles_before = {t['id']: t for t in old['tiles']}
    checks = {'inputs_current': all(sha(f) == h for f, h in change['input_sha256'].items()),
              'only_two_overlay_meshes_replaced': set(before) == set(after) and len(records) == 2 and
              {r['kind'] for r in records.values()} == {'shoulder', 'rockfall_net'},
              'all_other_mesh_records_and_bytes_preserved': all(after[k] == r and sha(r['source']) == r['sha256'] for k, r in before.items() if k not in records),
              'new_geometry_signatures': all(sha(r['source']) == r['sha256'] for r in records.values()),
              'unaffected_tile_records_and_bytes_preserved': all(t == tiles_before[t['id']] and sha(t['heightmap']) == t['height_sha256'] and sha(t['holes']) == t['holes_sha256'] for t in m['tiles'] if t['id'] != cfg['tile']),
              'all_holes_preserved': all(t['holes'] == tiles_before[t['id']]['holes'] and sha(t['holes']) == t['holes_sha256'] for t in m['tiles'])}
    tile = next(t for t in m['tiles'] if t['id'] == cfg['tile']); parent_tile = tiles_before[cfg['tile']]
    n = tile['samples']; step = tile['xy_scale_cm']/100; origin = np.array(tile['bounds_xy_cm'][:2])/100
    height = np.fromfile(tile['heightmap'], '<u2').reshape(n, n)
    previous = np.fromfile(parent_tile['heightmap'], '<u2').reshape(n, n)
    changed = height != previous; row, col = np.where(changed); xy = origin+np.c_[col, row]*step
    checks['modified_r16_signature'] = sha(tile['heightmap']) == tile['height_sha256']
    checks['native_tile_edges_unchanged'] = not (changed[0].any() or changed[-1].any() or changed[:, 0].any() or changed[:, -1].any())
    checks['modified_positions_match_declared_evidence'] = np.array_equal(xy, np.array(change['statistics']['changed_UE_xy_m']))
    section = m['rockfall_edges']['net_bank_sections']; edge = np.array(section['asphalt_edge_UE_xy_m'])
    normal = np.array(section['uphill_UE_xy_unit']); station = np.array(section['station_m'])
    segments = shapely.linestrings(np.stack([edge[:-1], edge[1:]], axis=1))
    ids = shapely.STRtree(segments).nearest(shapely.points(xy))
    delta = edge[ids+1]-edge[ids]
    f = np.clip(((xy-edge[ids])*delta).sum(1)/(delta*delta).sum(1), 0, 1)
    near = edge[ids]+f[:, None]*delta; normals = normal[ids]*(1-f[:, None])+normal[ids+1]*f[:, None]
    s = station[ids]*(1-f)+station[ids+1]*f
    ground = NativeGround(m); road = RoadSurface(m); _, dist = road.sample(xy*100, clamp_to_triangle=True)
    checks['changed_samples_only_in_reviewed_uphill_3m_scope'] = bool(len(xy) > 0 and (dist > 0).all() and (dist/100 < cfg['outer_offset_m']).all() and (((xy-near)*normals).sum(1) > 0).all() and (s > station[0]).all() and (s < station[-1]).all())
    # A modified vertex affects four native cells. Intersect those exact
    # native triangles with asphalt and test every polygon vertex: both
    # surfaces are affine on each intersection, so its extrema are covered.
    indices = np.c_[col, row]
    cells = np.unique(np.concatenate([indices+q for q in [[0, 0], [-1, 0], [0, -1], [-1, -1]]]), axis=0)
    corners = origin+(cells[:, None, :]+np.array([[[0, 0], [1, 0], [1, 1], [0, 1]]]))*step
    faces = corners[:, [[0, 1, 2], [0, 2, 3]], :].reshape(-1, 3, 2)
    polygons = shapely.polygons(faces*100); pairs = road.tree.query(polygons, predicate='intersects')
    clipped = shapely.intersection(polygons[pairs[0]], road.polygons[pairs[1]])
    sample = np.unique(np.round(shapely.get_coordinates(clipped), 7), axis=0)
    rz, dd = road.sample(sample, clamp_to_triangle=True); gz = ground.sample(sample/100)*100
    clearance = (rz-gz)/100
    checks['all_modified_native_asphalt_intersections_clear'] = bool(len(sample) > 0 and np.isfinite(clearance).all() and clearance.min() >= .01 and dd.max() < .001)
    net_gap = None; shoulder_area_error = None
    for r in records.values():
        data = json.loads(Path(r['source']).read_text()); v = (np.array(data['vertices_cm'])+r['location_cm'])/100
        tri = np.array(data['triangles']); face = v[tri]
        checks[r['id']+'_nondegenerate'] = bool(np.isfinite(v).all() and (np.linalg.norm(np.cross(face[:, 1]-face[:, 0], face[:, 2]-face[:, 0]), axis=1) > 1.e-10).all())
        original_data = json.loads(Path(before[r['id']]['source']).read_text()); old_v = (np.array(original_data['vertices_cm'])+before[r['id']]['location_cm'])/100
        if r['kind'] == 'rockfall_net':
            checks['net_plan_footprint_and_topology_preserved'] = bool(np.array_equal(tri, np.array(original_data['triangles'])) and np.array_equal(v[:, :2], old_v[:, :2]))
            points = np.concatenate([v, face.mean(1), (face[:, 0]+face[:, 1])/2, (face[:, 1]+face[:, 2])/2, (face[:, 2]+face[:, 0])/2])
            gap = points[:, 2]-ground.sample(points[:, :2]); net_gap = float(gap.min())
            checks['net_follows_native_triangle_interiors'] = bool(np.isfinite(gap).all() and np.abs(gap-m['rockfall_edges']['config']['net_vertical_standoff_m']).max() < 1.e-6)
            checks['net_no_physical_barrier'] = r['collision_enabled'] is False and 'collision_convexes_cm' not in data
        else:
            new_shape = shapely.union_all(shapely.polygons(face[:, :, :2]))
            old_shape = shapely.union_all(shapely.polygons(old_v[np.array(original_data['triangles']), :2]))
            shoulder_area_error = float(new_shape.symmetric_difference(old_shape).area)
            checks['shoulder_plan_footprint_preserved'] = shoulder_area_error < .002
            _, dd = road.sample(v[:, :2]*100, clamp_to_triangle=True)
            away = dd >= .15001*100
            checks['shoulder_outside_seam_on_native_ground'] = bool(np.abs(v[away, 2]-ground.sample(v[away, :2])-.02).max() < 1.e-5)
    curb = next(r for r in m['meshes'] if r['kind'] == 'rockfall_curb')
    data = json.loads(Path(curb['source']).read_text()); solids = (np.array(data['vertices_cm'])+curb['location_cm']).reshape(-1, 8, 3)/100
    footing = solids[:, :4].reshape(-1, 3); gap = footing[:, 2]-ground.sample(footing[:, :2])
    checks['unchanged_curb_footing_embedded'] = bool(np.isfinite(gap).all() and gap.max() < .02)
    draft = ROOT/'results/road_drafts'/m['build_id']; parent = Path(change['parent_draft'])
    a = json.loads((parent/'circuit_itinerary.json').read_text()); b = json.loads((draft/'circuit_itinerary.json').read_text())
    a.pop('build_id'); b.pop('build_id'); checks['all_itinerary_fields_preserved'] = a == b
    a = json.loads((parent/'circuit_driving_world.json').read_text()); b = json.loads((draft/'circuit_driving_world.json').read_text())
    a.pop('build_id'); b.pop('build_id')
    for aa, bb in zip(a['tiles'], b['tiles']): aa.pop('map'); bb.pop('map')
    checks['non_map_world_fields_preserved'] = a == b
    # Use the same fixed road transects that exposed the defect, rather than
    # selecting a favorable new camera or relocating the driving surface.
    diag_path = ROOT/'results/rockfall_bank_ripple_diagnostic_6108_v1.json'
    diag = json.loads(diag_path.read_text()); e = np.array(diag['edge_UE_xy_m']); u = np.array(diag['uphill_unit']); offsets = np.array(diag['offset_m'])
    points = e[:, None, :]+u[:, None, :]*offsets[None, :, None]
    z = ground.sample(points.reshape(-1, 2)).reshape(len(e), -1); prior = np.array(diag['derived_height_m']); source = np.array(diag['source_height_m'])
    comparisons = []
    for i, offset in enumerate(offsets):
        rms = lambda a: float(np.sqrt(np.mean(np.diff(a[:, i], n=2)**2)))
        comparisons.append({'offset_m': float(offset), 'source_second_difference_rms_m': rms(source), 'parent_second_difference_rms_m': rms(prior), 'new_second_difference_rms_m': rms(z)})
    checks['artificial_corrugation_reduced_over_50_percent_05_to_2m'] = all(r['new_second_difference_rms_m'] < .5*r['parent_second_difference_rms_m'] for r in comparisons if .5 <= r['offset_m'] <= 2.)
    checks['five_metre_source_transect_preserved_exactly'] = np.array_equal(z[:, -1], source[:, -1])
    report = {'build_id': m['build_id'], 'parent_build_id': old['build_id'], 'passed': all(checks.values()), 'checks': checks,
              'changed_samples': int(changed.sum()), 'asphalt_native_intersection_extrema_tested': len(sample),
              'minimum_asphalt_to_native_clearance_m': float(clearance.min()), 'minimum_net_gap_m': net_gap,
              'shoulder_footprint_symmetric_difference_m2': shoulder_area_error,
              'roughness_diagnostic_sha256': sha(diag_path), 'longitudinal_comparison': comparisons,
              'scope': 'Saved data and geometry only. Native import, physical drive and rendered fidelity remain separate.'}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)); print(json.dumps(report, indent=2))
    if not report['passed']: raise SystemExit(1)


if __name__ == '__main__': main()
