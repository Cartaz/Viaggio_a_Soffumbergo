"""Reuse an observed access only after exact local geometry/candidate checks."""
import argparse
import hashlib
import json
from pathlib import Path
import time


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def select(inventory, station):
    rows = [c for group in ['candidates', 'physical_diagnostic_candidates']
            for c in inventory.get(group, []) if c['station_m'] == station]
    if len(rows) != 1: raise RuntimeError('Access missing or ambiguous')
    return rows[0]


def main():
    parser = argparse.ArgumentParser()
    for name in ['review', 'baseline-inventory', 'inventory', 'baseline-manifest', 'manifest', 'output']:
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--station', type=float, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise RuntimeError('Preserve the previous evidence link')
    review = read(args.review); old_cases = read(args.baseline_inventory); cases = read(args.inventory)
    old = read(args.baseline_manifest); new = read(args.manifest)
    a = select(old_cases, args.station); b = select(cases, args.station)
    assert a == b and review['station_m'] == args.station
    assert review['access_suitable_for_physical_diagnostic'] is True
    assert review['build_id'] == old_cases['build_id'] == old['build_id']
    assert review['requested_wgs84'] == [b['latitude'], b['longitude']]
    assert cases['build_id'] == new['build_id'] and cases['manifest_sha256'] == sha(args.manifest)
    x, y, _ = b['center_UE_cm']; radius_cm = 2500
    tiles = [t for t in new['tiles'] if t['bounds_xy_cm'][0]-radius_cm <= x <= t['bounds_xy_cm'][2]+radius_cm
             and t['bounds_xy_cm'][1]-radius_cm <= y <= t['bounds_xy_cm'][3]+radius_cm]
    assert tiles
    guards = {}; tile_rows = []
    for t in tiles:
        previous = next(row for row in old['tiles'] if row['id'] == t['id'])
        for key in ['height_sha256', 'holes_sha256', 'samples', 'xy_scale_cm', 'z_scale', 'location_cm', 'bounds_xy_cm']:
            assert t[key] == previous[key], (t['id'], key)
        for key, hash_key in [('heightmap', 'height_sha256'), ('holes', 'holes_sha256')]:
            assert sha(t[key]) == t[hash_key]; guards[str(Path(t[key]).resolve())] = t[hash_key]
        tile_rows.append({'tile': t['id'], 'height_sha256': t['height_sha256'], 'holes_sha256': t['holes_sha256']})
    ids = {t['id'] for t in tiles}
    old_meshes = {m['id']: m for m in old['meshes'] if m.get('tile') in ids}
    new_meshes = {m['id']: m for m in new['meshes'] if m.get('tile') in ids}
    assert old_meshes == new_meshes and new_meshes
    mesh_rows = []
    for mesh in new_meshes.values():
        assert sha(mesh['source']) == mesh['sha256']
        guards[str(Path(mesh['source']).resolve())] = mesh['sha256']
        mesh_rows.append({'id': mesh['id'], 'source_sha256': mesh['sha256']})
    sources = [args.review, args.baseline_inventory, args.inventory, args.baseline_manifest, args.manifest, Path(__file__)]
    result = dict(review); result['build_id'] = new['build_id']; result['physically_driven_current_generation'] = False
    result['evidence_link'] = {'created_unix': time.time(), 'source_review': str(args.review.resolve()),
        'source_build_id': review['build_id'], 'new_streetview_observation': False,
        'diagnostic_candidate_payload_identical': True, 'local_radius_m': 25,
        'tiles': tile_rows, 'unchanged_local_meshes': mesh_rows, 'geometry_guard_sha256': guards,
        'source_sha256': {str(p.resolve()): sha(p) for p in sources},
        'scope': 'Same observed access at identical coordinates, candidate and local terrain/road/structure source geometry. '
                 'No transfer of previous driving success, no claim of complete wider anthropic context, '
                 'and no assumption that new vegetation or runtime behaves identically; new physical diagnostic required.'}
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'saved': str(args.output), 'build_id': new['build_id'], 'tiles': sorted(ids),
                      'candidate_identical': True, 'physical_success_transferred': False}))


if __name__ == '__main__': main()
