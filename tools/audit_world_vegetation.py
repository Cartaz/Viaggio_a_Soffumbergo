"""Audit actual saved PCG transforms against all geometry and native terrain."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import shapely
from prepare_reentry_checks import NativeGround

ROOT = Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(); p.add_argument('--draft', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); args = p.parse_args()
    if args.output.exists(): raise RuntimeError('Preserve prior vegetation audit')
    imported = json.loads((args.draft/'import_report.json').read_text()); assert imported['all_imported']
    m = json.loads(Path(imported['manifest']).read_text()); v = m['vegetation']
    old = json.loads(Path(v['parent_manifest']).read_text()); masks = json.loads(Path(v['mask_manifest']).read_text())
    journal = json.loads(Path(imported['journal']).read_text()); base = shapely.geometry.shape(json.loads(Path(masks['base_exclusions']).read_text()))
    coordinates, owners = shapely.get_coordinates(shapely.get_parts(base.boundary), return_index=True)
    same_ring = owners[:-1] == owners[1:]
    segments = shapely.linestrings(np.stack([coordinates[:-1][same_ring], coordinates[1:][same_ring]], axis=1))
    boundary_tree = shapely.STRtree(segments); shapely.prepare(base)
    ground = NativeGround(m); old_tiles = {t['id']: t for t in old['tiles']}; mask_tiles = {t['tile']: t for t in masks['tiles']}
    branches = {name: b for b in v['config']['branches'] for name in b['meshes']}
    checks = {'matching_native_import': imported['build_id'] == journal['build_id'] == m['build_id'] and journal['all_imported'],
        'all_eligible_tiles_generated': set(journal['tiles']) == set(v['changed_tiles']),
        'all_geometry_inputs_current': all(sha(f) == h for f, h in v['input_sha256'].items()),
        'all_parent_protected_files_unchanged': all(sha(f) == h for f, h in journal['protected_before'].items()),
        'every_road_structure_and_overlay_record_and_byte_preserved': m['meshes'] == old['meshes'] and all(sha(r['source']) == r['sha256'] for r in m['meshes']),
        'all_113_heightfields_and_holes_preserved': len(m['tiles']) == 113 and all(t['heightmap'] == old_tiles[t['id']]['heightmap'] and t['holes'] == old_tiles[t['id']]['holes'] and sha(t['heightmap']) == t['height_sha256'] and sha(t['holes']) == t['holes_sha256'] for t in m['tiles'])}
    rows = []; totals = {}; minimum_envelope_clearance = float('inf'); max_ground_error = 0.
    for tile in m['tiles']:
        if tile['id'] not in journal['tiles']: continue
        record = journal['tiles'][tile['id']]; mask_row = mask_tiles[tile['id']]
        with gzip.open(record['instance_rows'], 'rt', encoding='utf-8') as stream: points = json.load(stream)
        digest = hashlib.sha256(json.dumps(points, separators=(',', ':')).encode()).hexdigest()
        valid = record['saved_complete'] and sha(record['instance_rows']) == record['instance_rows_sha256'] and digest == record['reload_snapshot']['sha256']
        valid = valid and all(r['sha256'] == digest for r in [record['runs'][0], record['runs'][1], record['runs'][3]])
        valid = valid and (not points or record['runs'][2]['sha256'] != digest)
        readback = record['native_terrain_readback']; valid = valid and readback['passed'] and readback['height_mismatches'] == readback['visibility_mismatches'] == 0
        valid = valid and all(q['passed'] for q in record['native_trunk_collision_probes'])
        map_file = ROOT/'Unreal/Content'/(tile['map'].removeprefix('/Game/')+'.umap')
        valid = valid and sha(map_file) == record['saved_map_sha256']
        local_min = None; local_max = 0.; bad_slope = 0; bad_mask = 0; bad_scale = 0; plant_envelope_errors = 0
        if points:
            a = np.array([r[1:] for r in points]); xy = a[:, :2]/100
            gz = ground.sample(xy); error = np.abs(a[:, 2]/100-gz); local_max = float(error.max()); max_ground_error = max(max_ground_error, local_max)
            pairs, dd = boundary_tree.query_nearest(shapely.points(xy), all_matches=False, return_distance=True)
            distance = np.empty(len(xy)); distance[pairs[0]] = dd
            distance[shapely.intersects_xy(base, xy[:, 0], xy[:, 1])] = 0
            for name in sorted({r[0] for r in points}):
                ids = np.array([i for i, r in enumerate(points) if r[0] == name]); branch = branches[name]
                totals[name] = totals.get(name, 0)+len(ids)
                radius = journal['mesh_info'][name]['maximum_plan_envelope_radius_m']/branch['max_scale']*a[ids, 7]
                clearance = distance[ids]-radius; c = float(clearance.min()); local_min = c if local_min is None else min(local_min, c)
                minimum_envelope_clearance = min(minimum_envelope_clearance, c); plant_envelope_errors += int((clearance < .05).sum())
                allowed = np.fromfile(mask_row['branches'][branch['id']]['mask_file'], 'u1').reshape(tile['samples'], tile['samples'])
                coordinate = np.floor((a[ids, :2]-mask_row['origin_cm'][:2])/mask_row['spacing_cm']+.5).astype(int)
                bad_mask += int((allowed[coordinate[:, 1], coordinate[:, 0]] != 1).sum())
                bad_scale += int(((a[ids, 7] < branch['min_scale']-.00001) | (a[ids, 7] > branch['max_scale']+.00001)).sum())
            values = np.fromfile(tile['heightmap'], '<u2').reshape(tile['samples'], tile['samples']).astype(float)
            q = (xy-np.array(tile['bounds_xy_cm'][:2])/100)/(tile['xy_scale_cm']/100); cell = np.floor(q).astype(int); f = q-cell; x, y = cell.T
            aa = values[y, x]; bb = values[y, x+1]; cc = values[y+1, x]; dd = values[y+1, x+1]
            dx = np.where(f[:, 0] >= f[:, 1], bb-aa, dd-cc)*ground.quant/(tile['xy_scale_cm']/100)
            dy = np.where(f[:, 0] >= f[:, 1], dd-bb, cc-aa)*ground.quant/(tile['xy_scale_cm']/100)
            up = 1/np.sqrt(1+dx*dx+dy*dy)
            bad_slope = sum(up[i] < math.cos(math.radians(branches[r[0]]['max_slope_degrees']))-1.e-6 for i, r in enumerate(points))
            valid = valid and np.isfinite(error).all() and local_max <= .02 and not (bad_slope or bad_mask or bad_scale or plant_envelope_errors)
        rows.append({'tile': tile['id'], 'passed': bool(valid), 'native_instances_checked': len(points), 'maximum_ground_error_m': local_max,
            'minimum_whole_plant_envelope_clearance_m': local_min, 'slope_violations': int(bad_slope), 'mask_violations': bad_mask, 'scale_violations': bad_scale, 'plant_envelope_violations': plant_envelope_errors})
        print('WORLD_PCG_AUDIT '+tile['id']+' '+str(bool(valid)), flush=True)
    checks['all_actual_native_plant_transforms_valid'] = all(t['passed'] for t in rows)
    checks['same_total_as_native_import'] = sum(t['native_instances_checked'] for t in rows) == imported['native_instances']
    report = {'build_id': m['build_id'], 'passed': all(checks.values()), 'checks': checks, 'tiles': rows, 'native_counts': totals,
        'total_instances': sum(totals.values()), 'maximum_native_ground_error_m': max_ground_error,
        'minimum_whole_plant_envelope_clearance_m': minimum_envelope_clearance,
        'scope': 'Every saved native PCG transform, seed/reload evidence, source terrain and existing structures. Rendered appearance, vehicle contact, complete driven laps and performance remain separate.'}
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)); print('WORLD_PCG_AUDIT_PASSED '+str(report['passed']))
    if not report['passed']: raise SystemExit(1)


if __name__ == '__main__': main()
