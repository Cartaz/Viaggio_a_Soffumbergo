"""Exclude ambiguous managed land without rewriting the first full mask artifact."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from pyproj import Transformer
import shapely

ROOT = Path(__file__).resolve().parents[1]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(); p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--config', type=Path, required=True); args = p.parse_args()
    old = json.loads(args.manifest.read_text()); cfg = json.loads(args.config.read_text())
    world = json.loads(Path(old['parent_manifest']).read_text()); origin = world['origin_ENH_m']
    projection = Transformer.from_crs(4326, 6708, always_xy=True); features = {}; geoms = []
    for name in old['config']['sources']:
        for f in json.loads((ROOT/name/'cover.geojson').read_text())['features']:
            features[f['id']] = f
    for f in features.values():
        if f['properties'].get('landuse') not in cfg['landuse']: continue
        g = shapely.geometry.shape(f['geometry'])
        if g.geom_type not in ['Polygon', 'MultiPolygon']: continue
        g = shapely.transform(g, projection.transform, interleaved=False)
        g = shapely.transform(g, lambda a: np.c_[a[:, 0]-origin[0], origin[1]-a[:, 1]])
        if not g.is_valid: g = shapely.make_valid(g)
        geoms.append(g)
    managed = shapely.union_all(geoms)
    inputs = [args.manifest, args.config, Path(__file__)]
    for t in old['tiles']: inputs += [Path(t['cover_file'])]+[Path(b['mask_file']) for b in t['branches'].values()]
    signatures = {**old['input_sha256'], **{str(f.resolve()): sha(f) for f in inputs}}
    build = hashlib.sha256(json.dumps(signatures, sort_keys=True).encode()).hexdigest()[:12]
    folder = ROOT/'terrain/world_vegetation_masks'/build
    if folder.exists(): raise RuntimeError('Preserve previous refinement')
    folder.mkdir(parents=True); m = copy.deepcopy(old); m['mask_build_id'] = build; m['input_sha256'] = signatures
    m['managed_land_refinement'] = {'parent_mask_manifest': str(args.manifest.resolve()), 'config': cfg, 'features': len(geoms)}
    m['config']['managed_land_policy'] = cfg
    base = shapely.geometry.shape(json.loads(Path(old['base_exclusions']).read_text())).union(managed)
    path = folder/'base_exclusions.geojson'; path.write_text(json.dumps(shapely.geometry.mapping(base))); m['base_exclusions'] = str(path)
    exclusions = {}
    for b in m['config']['branches']:
        margin = m['tiles'][0]['spacing_cm']/100/np.sqrt(2)+m['config']['sampling_guard_m']
        extra = managed.buffer(b['plant_radius_m']+margin)
        old_exclusion = shapely.geometry.shape(json.loads(Path(old['branch_exclusions'][b['id']]).read_text()))
        path = folder/(b['id']+'_exclusions.geojson'); path.write_text(json.dumps(shapely.geometry.mapping(old_exclusion.union(extra))))
        m['branch_exclusions'][b['id']] = str(path); exclusions[b['id']] = extra; shapely.prepare(extra)
    removed = {b['id']: 0 for b in m['config']['branches']}; totals = dict.fromkeys(removed, 0)
    for t in m['tiles']:
        n = t['width']; x, y = np.meshgrid(t['origin_cm'][0]/100+np.arange(n)*t['spacing_cm']/100, t['origin_cm'][1]/100+np.arange(n)*t['spacing_cm']/100)
        for name, b in t['branches'].items():
            a = np.fromfile(b['mask_file'], 'u1').reshape(n, n); kill = (a != 0) & shapely.intersects_xy(exclusions[name], x, y)
            count = int(kill.sum()); removed[name] += count
            if count:
                a[kill] = 0; path = folder/(t['tile']+'_'+name+'.bin'); a.tofile(path)
                b.update(mask_file=str(path), mask_sha256=sha(path), allowed_cells=int(a.sum()))
            totals[name] += b['allowed_cells']
        print('MANAGED_MASK '+t['tile'], flush=True)
    m['allowed_cells_per_branch'] = totals; m['managed_land_refinement']['removed_cells_per_branch'] = removed
    output = folder/'manifest.json'; output.write_text(json.dumps(m, indent=2)); print('REFINED_MASK_MANIFEST '+str(output), flush=True)


if __name__ == '__main__': main()
