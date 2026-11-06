"""Check all accepted mask samples against saved geometry and native NoData."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import shapely

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(); p.add_argument('--manifest', type=Path, required=True); args = p.parse_args()
    output = args.manifest.parent/'mask_audit.json'
    if output.exists(): raise RuntimeError('Preserve previous mask audit')
    m = json.loads(args.manifest.read_text()); parent = json.loads(Path(m['parent_manifest']).read_text())
    by_id = {t['id']: t for t in parent['tiles']}
    checks = {'all_113_source_tiles_present': len(m['tiles']) == len(parent['tiles']) == 113,
              'inputs_current': all(sha(f) == h for f, h in m['input_sha256'].items())}
    exclusions = {k: shapely.geometry.shape(json.loads(Path(p).read_text())) for k, p in m['branch_exclusions'].items()}
    for g in exclusions.values(): shapely.prepare(g)
    rows = []
    for t in m['tiles']:
        source = by_id[t['tile']]; n = t['width']; cover = np.fromfile(t['cover_file'], 'u1').reshape(n, n)
        holes = np.fromfile(source['holes'], 'u1').reshape(n, n); padded = np.pad(holes, 1, mode='edge')
        unavailable = np.logical_or.reduce([padded[y:y+n, x:x+n] != 0 for y in range(3) for x in range(3)])
        valid = sha(t['cover_file']) == t['cover_sha256'] and t['origin_cm'][:2] == source['bounds_xy_cm'][:2] and t['spacing_cm'] == source['xy_scale_cm']
        valid = valid and t['source_height_sha256'] == sha(source['heightmap']) and t['source_holes_sha256'] == sha(source['holes'])
        counts = {}
        for branch in m['config']['branches']:
            b = t['branches'][branch['id']]; a = np.fromfile(b['mask_file'], 'u1').reshape(n, n); allowed = a != 0
            rr, cc = np.where(allowed)
            x = t['origin_cm'][0]/100+cc*t['spacing_cm']/100; y = t['origin_cm'][1]/100+rr*t['spacing_cm']/100
            outside = not shapely.intersects_xy(exclusions[branch['id']], x, y).any()
            passed = sha(b['mask_file']) == b['mask_sha256'] and np.isin(a, [0, 1]).all() and int(allowed.sum()) == b['allowed_cells']
            passed = passed and not (allowed[-1].any() or allowed[:, -1].any()) and not allowed[unavailable].any()
            passed = passed and np.isin(cover[allowed], branch['cover_classes']).all() and outside
            counts[branch['id']] = {'passed': bool(passed), 'all_accepted_cells_checked': len(rr)}; valid = valid and passed
        rows.append({'tile': t['tile'], 'passed': bool(valid), 'branches': counts})
        print('MASK_AUDIT '+t['tile']+' '+str(bool(valid)), flush=True)
    checks['all_masks_cover_ownership_nodata_and_exclusion_checks'] = all(t['passed'] for t in rows)
    report = {'passed': all(checks.values()), 'mask_build_id': m['mask_build_id'], 'checks': checks, 'tiles': rows,
              'scope': 'All saved accepted mask cells and their geometry/NoData/ownership constraints. Native PCG instances and performance are not covered.'}
    output.write_text(json.dumps(report, indent=2)); print('MASK_AUDIT_PASSED '+str(report['passed']))
    if not report['passed']: raise SystemExit(1)


if __name__ == '__main__': main()
