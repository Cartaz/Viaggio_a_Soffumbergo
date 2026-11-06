"""Prepare an isolated local bank derivative and conform its existing overlays."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from bank_transition import refit
from native_shoulder_overlay import overlay
from prepare_reentry_checks import NativeGround
from road_surface import RoadSurface

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--parent-draft', type=Path, required=True)
    p.add_argument('--config', type=Path, required=True)
    args = p.parse_args()
    parent = args.parent_draft.resolve()
    imported = json.loads((parent/'import_report.json').read_text())
    assert imported['all_imported']
    parent_path = Path(imported['manifest']); original = json.loads(parent_path.read_text())
    config = json.loads(args.config.read_text())
    source_path = ROOT/'terrain/world_tiles/manifest.json'
    source = json.loads(source_path.read_text())
    inputs = [parent_path, source_path, args.config, ROOT/config['source_review'],
              parent/'circuit_driving_world.json', parent/'circuit_itinerary.json',
              Path(__file__), ROOT/'tools/bank_transition.py', ROOT/'tools/native_shoulder_overlay.py',
              ROOT/'tools/road_clearance.py', ROOT/'tools/prepare_reentry_checks.py', ROOT/'tools/road_surface.py',
              ROOT/'tools/audit_bank_transition.py', ROOT/'tools/import_bank_transition.py']
    fingerprints = {str(f.resolve()): sha(f) for f in inputs}
    build = hashlib.sha256(json.dumps(fingerprints, sort_keys=True).encode()).hexdigest()[:12]
    folder = ROOT/'terrain/bank_transitions'/build; draft = ROOT/'results/road_drafts'/build
    if folder.exists() or draft.exists():
        raise RuntimeError('Preserve existing derivative')
    folder.mkdir(parents=True); draft.mkdir(parents=True)
    road = RoadSurface(original)
    tile, raster, stats = refit(original, source, road, config)
    height_path = folder/(tile['id']+'.r16'); raster.tofile(height_path)
    m = copy.deepcopy(original); m['build_id'] = build
    changed_tile = next(t for t in m['tiles'] if t['id'] == tile['id'])
    for key in list(changed_tile):
        if key.endswith('_parent_map'): changed_tile.pop(key)
    changed_tile.update(bank_parent_map=tile['map'], map='/Game/World/Driving/B_'+build+'/Terrain/'+tile['id'],
                        heightmap=str(height_path), height_sha256=sha(height_path))
    raw_tile = next(t for t in source['tiles'] if t['id'] == tile['id'])
    raw = np.fromfile(raw_tile['heightmap'], '<u2').reshape(raster.shape)
    delta = (raster.astype(float)-raw)*source['height_quantization_m']
    changed_tile.update(max_grading_delta_m=float(np.abs(delta).max()), changed_samples=int(np.count_nonzero(delta)))
    rr, cc = np.unravel_index(np.abs(delta).argmax(), delta.shape)
    ground = NativeGround(m)
    peak_xy = np.asarray(tile['bounds_xy_cm'][:2])/100+np.array([cc, rr])*tile['xy_scale_cm']/100
    changed_tile.update(peak_change_UE_m=[*peak_xy.tolist(), float(ground.sample(peak_xy)[0])],
                        peak_source_height_local_m=float(raw[rr, cc]*ground.quant+ground.zero),
                        peak_delta_m=float(delta[rr, cc]))
    records = []; diagnostics = []
    for old in original['meshes']:
        if old['tile'] != tile['id'] or old['kind'] not in ['shoulder', 'rockfall_net']:
            continue
        if old['kind'] == 'shoulder':
            vertices, triangles, diagnostic = overlay(changed_tile, old, ground, road)
            local = np.round(vertices*100-old['location_cm'], 5)
            cross = np.cross(local[triangles[:, 1]]-local[triangles[:, 0]], local[triangles[:, 2]]-local[triangles[:, 0]])
            keep = (cross*cross).sum(1) >= 1.e-8
            diagnostic['creator_precision_removed'] = int((~keep).sum()); triangles = triangles[keep]
            payload = {'vertices_cm': local.tolist(), 'triangles': triangles.tolist()}
            diagnostics.append(diagnostic)
        else:
            payload = json.loads(Path(old['source']).read_text())
            vertices = (np.asarray(payload['vertices_cm'])+old['location_cm'])/100
            vertices[:, 2] = ground.sample(vertices[:, :2])+m['rockfall_edges']['config']['net_vertical_standoff_m']
            if not np.isfinite(vertices).all(): raise ValueError('Net on missing ground')
            local = np.round(vertices*100-old['location_cm'], 6)
            payload['vertices_cm'] = local.tolist(); triangles = np.asarray(payload['triangles'])
        f = folder/(old['id']+'.json'); f.write_text(json.dumps(payload, separators=(',', ':')))
        records.append({**old, 'source': str(f), 'sha256': sha(f),
                        'asset': '/Game/World/Driving/B_'+build+'/Meshes/'+old['id'],
                        'vertices': len(local), 'triangles': len(triangles)})
    replacements = {r['id']: r for r in records}
    m['meshes'] = [replacements.get(r['id'], r) for r in original['meshes']]
    m['rockfall_edges']['records'] = [replacements.get(r['id'], r) for r in m['rockfall_edges']['records']]
    net = next(r for r in records if r['kind'] == 'rockfall_net')
    data = json.loads(Path(net['source']).read_text()); v = np.asarray(data['vertices_cm'])+net['location_cm']
    m['rockfall_edges']['net_surface_centers_cm'] = v[np.asarray(data['triangles'])].mean(1).tolist()
    m['rockfall_edges']['bank_refit_build_id'] = build
    m['bank_transition'] = {'parent_build_id': original['build_id'], 'parent_manifest': str(parent_path),
                            'parent_draft': str(parent), 'input_sha256': fingerprints, 'config': config,
                            'records': records, 'statistics': stats, 'shoulder_diagnostics': diagnostics,
                            'scope': 'Local native engineering cut; unchanged asphalt, curb, rails, route, original DTM and all holes. Existing net footprint follows the new native triangles. Earlier parent audit results remain historical.'}
    m['report'].update(build_id=build, native_imported=False, full_lap_driven=False)
    manifest = folder/'manifest.json'; manifest.write_text(json.dumps(m, indent=2))
    world = json.loads((parent/'circuit_driving_world.json').read_text()); world['build_id'] = build
    for t in world['tiles']:
        if t['id'] == tile['id']: t['map'] = changed_tile['map']
    (draft/'circuit_driving_world.json').write_text(json.dumps(world))
    route = json.loads((parent/'circuit_itinerary.json').read_text()); route['build_id'] = build
    (draft/'circuit_itinerary.json').write_text(json.dumps(route))
    report = {'build_id': build, 'parent_build_id': original['build_id'], 'manifest': str(manifest),
              'draft': str(draft), 'change_kind': 'local_native_bank_transition', 'activated': False,
              'changed_samples': stats['changed_samples'], 'replaced_meshes': [r['id'] for r in records]}
    (draft/'structure_preparation.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
