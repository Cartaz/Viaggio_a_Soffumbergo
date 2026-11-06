"""Prepare a source-linked local finish on existing shoulder geometry only."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import shapely
from PIL import Image
from road_surface import RoadSurface

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--parent-draft', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    parent = args.parent_draft.resolve()
    imported = json.loads((parent/'import_report.json').read_text())
    assert imported['all_imported']
    manifest_path = Path(imported['manifest'])
    original = json.loads(manifest_path.read_text())
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    review = ROOT/cfg['source_review']; audit_path = ROOT/cfg['margin_audit']
    audit = json.loads(audit_path.read_text())
    assert audit['audit_completed'] and audit['source_inputs_unchanged']
    assert audit['build_id'] == original['build_id']
    assert all(sha(p) == value for p, value in audit['protected_input_sha256'].items())
    csv_path = audit_path.with_name('cross_sections.csv')
    assert sha(csv_path) == audit['cross_sections_sha256']
    paths = [manifest_path, parent/'circuit_driving_world.json', parent/'circuit_itinerary.json',
             args.config, Path(__file__), review, audit_path, csv_path]
    inputs = {str(p.resolve()): sha(p) for p in paths}
    build = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:12]
    folder = ROOT/'terrain/drainage_surfaces'/build
    draft = ROOT/'results/road_drafts'/build
    if folder.exists() or draft.exists():
        raise RuntimeError('Preserve earlier preparation')
    # The audit has ten width samples at each surveyed cross-section. Recover
    # its two endpoints algebraically; no new terrain interpolation is used.
    rows = np.genfromtxt(csv_path, delimiter=',', names=True)
    groups = rows.reshape(-1, len(audit['fractional_width_samples']))
    lo, hi = groups[:, 0], groups[:, -1]
    a = np.column_stack([lo['UE_x_m'], lo['UE_y_m']])
    b = np.column_stack([hi['UE_x_m'], hi['UE_y_m']])
    vector = (b-a)/(hi['gap_fraction']-lo['gap_fraction'])[:, None]
    edges = a-vector*lo['gap_fraction'][:, None]
    inner = edges+vector
    # Remove repeated joint endpoints, retaining the original traversal order.
    keep = np.r_[True, np.linalg.norm(np.diff(inner, axis=0), axis=1) > 1.e-7]
    inner = inner[keep]; edges = edges[keep]
    band = shapely.Polygon(np.vstack([inner, edges[::-1]]))
    assert band.is_valid and not band.is_empty and band.area > 0
    road = RoadSurface(original)
    box = np.asarray(band.bounds)*100 + np.array([-100, -100, 100, 100])
    ids = road.tree.query(shapely.box(*box), predicate='intersects')
    asphalt = shapely.transform(shapely.union_all(road.polygons[ids]), lambda p: p/100)
    curb = next(r for r in original['rockfall_edges']['records'] if r['kind'] == 'rockfall_curb')
    mesh = json.loads(Path(curb['source']).read_text())
    solids = (np.asarray(mesh['vertices_cm'])+curb['location_cm']).reshape(-1, 8, 3)/100
    curb_footprint = shapely.union_all(shapely.polygons(solids[:, :4, :2]))
    band = band.difference(asphalt).difference(curb_footprint)
    assert band.is_valid and not band.is_empty and band.area > 0
    step = cfg['pixel_size_m']; pad = cfg['texture_border_m']
    assert step > 0 and cfg['mask_inset_m'] > np.sqrt(2)*step
    bounds = np.asarray(band.bounds)
    origin = np.floor((bounds[:2]-pad)/step)*step
    needed = np.ceil((bounds[2:]+pad-origin)/step).astype(int)
    size = 2**np.ceil(np.log2(needed)).astype(int)
    x = origin[0]+(np.arange(size[0])+.5)*step
    y = origin[1]+(np.arange(size[1])+.5)*step
    xx, yy = np.meshgrid(x, y)
    points = shapely.points(np.column_stack([xx.ravel(), yy.ravel()]))
    inside = shapely.contains(band, points)
    distance = np.zeros(len(points))
    distance[inside] = shapely.distance(points[inside], band.boundary)
    weight = np.clip((distance-cfg['mask_inset_m'])/cfg['mask_feather_m'], 0, 1)
    mask = np.rint(weight*255).astype('uint8').reshape(len(y), len(x))
    assert mask.max() == 255 and np.count_nonzero(mask) > 0
    assert not mask[0].any() and not mask[-1].any() and not mask[:, 0].any() and not mask[:, -1].any()
    active_distance = distance[mask.ravel() > 0]
    # Bilinear nonzero support reaches at most sqrt(2)*step from a texel center.
    clearance = float(active_distance.min()-np.sqrt(2)*step)
    assert clearance > 0
    folder.mkdir(parents=True); draft.mkdir(parents=True)
    image_path = folder/'drainage_mask.png'
    Image.fromarray(mask).save(image_path)
    polygon_path = folder/'margin_UE_xy_m.geojson'
    polygon_path.write_text(shapely.to_geojson(band))
    m = copy.deepcopy(original); m['build_id'] = build
    tile = next(t for t in m['tiles'] if t['id'] == cfg['tile'])
    tile['drainage_parent_map'] = tile['map']
    tile['map'] = '/Game/World/Driving/G_'+build+'/Terrain/'+cfg['tile']
    m['drainage_surface'] = {
        'parent_build_id': original['build_id'], 'parent_draft': str(parent),
        'parent_manifest': str(manifest_path), 'input_sha256': inputs, 'config': cfg,
        'mask_file': str(image_path), 'mask_sha256': sha(image_path),
        'texture_asset': '/Game/World/Driving/G_'+build+'/Materials/T_DrainageMask',
        'material_asset': '/Game/World/Driving/G_'+build+'/Materials/M_DrainageShoulder',
        'uv_origin_UE_xy_cm': (origin*100).tolist(),
        'uv_span_xy_cm': (size*step*100).tolist(), 'texture_size_xy': size.tolist(),
        'mask_polygon': str(polygon_path), 'geometry_and_collision_changed': False,
        'native_imported': False, 'visually_accepted': False,
    }
    manifest = folder/'manifest.json'; manifest.write_text(json.dumps(m, indent=2))
    for name in ['circuit_driving_world.json', 'circuit_itinerary.json']:
        data = json.loads((parent/name).read_text()); data['build_id'] = build
        if 'tiles' in data:
            for item in data['tiles']:
                if item['id'] == cfg['tile']: item['map'] = tile['map']
        (draft/name).write_text(json.dumps(data))
    checked = all(sha(p) == value for p, value in inputs.items())
    mask_report = {'build_id': build, 'passed': checked, 'texture_size_xy': size.tolist(),
        'band_area_m2': float(band.area), 'nonzero_texels': int(np.count_nonzero(mask)),
        'bilinear_nonzero_support_clearance_lower_bound_m': clearance,
        'texture_filter_assumption': 'Bilinear at base mip; mipmaps must be disabled in native import.',
        'original_inputs_unchanged': checked, 'native_engine_executed': False,
        'rendering_executed': False, 'geometry_and_collision_changed': False,
        'scope': 'Finite centerline cross-section polygon and mathematical base-mip bilinear mask support. Not native UV, pixel or drainage engineering acceptance.'}
    (draft/'drainage_mask_audit.json').write_text(json.dumps(mask_report, indent=2))
    preparation = {'build_id': build, 'parent_build_id': original['build_id'],
        'manifest': str(manifest), 'draft': str(draft), 'change_kind': 'local_drainage_finish_only',
        'changed_tiles': [cfg['tile']], 'diagnostic_only': False, 'activated': False,
        'geometry_and_collision_changed': False, 'native_imported': False}
    (draft/'structure_preparation.json').write_text(json.dumps(preparation, indent=2))
    print(json.dumps({**preparation, 'mask_audit': mask_report}, indent=2))


if __name__ == '__main__':
    main()
