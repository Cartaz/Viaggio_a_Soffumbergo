"""Publish only verified native tiles to runtime; exact grid-point survey inputs."""
import json
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
m = json.loads((root / 'terrain/world_tiles/manifest.json').read_text())
proof = json.loads((root / 'results/world_tiles_import.json').read_text())
assert proof['all_imported_and_verified']
for tile in m['tiles']:
    record = proof['tiles'][tile['id']]
    assert record['verification']['passed'] and record['height_sha256'] == tile['height_sha256'] and record['holes_sha256'] == tile['holes_sha256']
origin = m['origin_ENH_m']
lookup = {(t['tx'], t['ty']): t for t in m['tiles']}
arrays = {t['id']: np.fromfile(t['heightmap'], '<u2').reshape(1009, 1009) for t in m['tiles']}
holes = {t['id']: np.fromfile(t['holes'], 'u1').reshape(1009, 1009) for t in m['tiles']}
mosaic = json.loads((root / 'terrain/lidar_mosaic/manifest.json').read_text())
e0, n0 = mosaic['origin_E_N_m']
valid_source = np.load(root / 'terrain/lidar_mosaic/height_m.npy', mmap_mode='r')
points = []

def add_sample(e, n):
    col = round((e-e0)/m['step_m']); row = round((n0-n)/m['step_m'])
    if row < 1 or col < 1 or not np.isfinite(valid_source[row-1:row+2,col-1:col+2]).all():
        return
    tx, x = divmod(col, m['tile_quads']); ty, y = divmod(row, m['tile_quads'])
    tile = lookup.get((tx, ty))
    if tile is None or holes[tile['id']][y, x]:
        raise ValueError('Survey sample outside valid terrain')
    h = int(arrays[tile['id']][y, x]) * m['height_quantization_m'] + m['source_height_bounds_m'][0]
    points.append([(e0+col*m['step_m']-origin[0])*100, (origin[1]-n0+row*m['step_m'])*100, (h-origin[2])*100])

route = json.loads((root / 'terrain/lidar_mosaic/candidate_route_ground_samples.json').read_text())
for sector in route['sectors']:
    for p in sector['coordinates_ENH_m']:
        add_sample(*p[:2])
route_points = len(points)
# Add valid points on both sides of every shared map edge. The route survey is
# sampled at nearest original grid centers (<=0.354 m), not a driven car path.
for seam in m['seams']:
    a = next(t for t in m['tiles'] if t['id'] == seam['a'])
    b = next(t for t in m['tiles'] if t['id'] == seam['b'])
    for k in range(10, 1000, 63):
        for offset in [-1, 0, 1]:
            x, y = (1008+offset, k) if b['tx'] > a['tx'] else (k, 1008+offset)
            col = a['tx']*1008+x; row = a['ty']*1008+y
            tx, lx = divmod(col, 1008); ty, ly = divmod(row, 1008)
            target = lookup.get((tx, ty))
            if target and not holes[target['id']][ly, lx]:
                add_sample(e0+col*0.5, n0-row*0.5)
data = {'origin_ENH_m': origin, 'tiles': [{k:t[k] for k in ['id','map','bounds_xy_cm']} for t in m['tiles']],
        'survey_points_cm': points, 'route_grid_samples': route_points,
        'seam_grid_samples': len(points)-route_points,
        'survey_scope': 'Exact original grid centers nearest candidate route, then both sides of shared tile boundaries; no driving test'}
(root / 'Unreal/Content/Data/circuit_world.json').write_text(json.dumps(data), encoding='utf-8')
validation = [r['verification'] for r in proof['tiles'].values()]
summary = {'tiles': len(validation), 'all_saved_native_tiles_verified': True,
           'height_samples_read': sum(r['samples_read'] for r in validation),
           'height_mismatches': sum(r['height_mismatches'] for r in validation),
           'visibility_mismatches': sum(r['visibility_mismatches'] for r in validation),
           'valid_ray_hits': sum(r['valid_ray_hits'] for r in validation),
           'hole_ray_misses': sum(r['hole_ray_misses'] for r in validation),
           'max_collision_error_cm': max(r['max_height_error_cm'] for r in validation),
           'shared_raster_edges_equal': len(m['seams']),
           'runtime_streaming_verified': False, 'entire_route_driven': False}
(root / 'results/world_terrain_validation.json').write_text(json.dumps(summary, indent=2))
m['native_import_verified'] = True
(root / 'terrain/world_tiles/manifest.json').write_text(json.dumps(m, indent=2))
print(json.dumps(summary)); print(json.dumps({'survey_points':len(points),'route_grid_samples':route_points}))
