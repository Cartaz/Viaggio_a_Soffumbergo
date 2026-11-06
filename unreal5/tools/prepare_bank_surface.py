"""Version an observed bank's material mask; preserve all source geometry."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
import shapely

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--parent-draft', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=ROOT/'parameters/costalunga_surface_v1.json')
    args = parser.parse_args()
    parent = args.parent_draft.resolve()
    imported = json.loads((parent/'import_report.json').read_text())
    assert imported['all_imported']
    original_path = Path(imported['manifest'])
    original = json.loads(original_path.read_text())
    cfg = json.loads(args.config.read_text())
    tile = next(t for t in original['tiles'] if t['id'] == cfg['tile'])
    record = next(r for r in original['meshes'] if r['id'] == cfg['footprint_mesh'])
    assert record['tile'] == cfg['tile'] and sha(record['source']) == record['sha256']
    source_review = ROOT/cfg['source_review']
    inputs = [original_path, parent/'circuit_driving_world.json', parent/'circuit_itinerary.json',
              args.config.resolve(), source_review, Path(record['source']), Path(tile['heightmap']), Path(tile['holes']),
              Path(__file__), ROOT/'tools/import_bank_surface.py']
    signatures = {str(p.resolve()): sha(p) for p in inputs}
    build = hashlib.sha256(json.dumps(signatures, sort_keys=True).encode()).hexdigest()[:12]
    folder = ROOT/'terrain/bank_surfaces'/build
    draft = ROOT/'results/road_drafts'/build
    if folder.exists() or draft.exists():
        raise RuntimeError('Preserve earlier surface variant')
    mesh = json.loads(Path(record['source']).read_text())
    vertices = (np.array(mesh['vertices_cm'])+np.array(record['location_cm']))/100
    triangles = vertices[np.array(mesh['triangles']), :2]
    polygons = shapely.polygons(triangles)
    footprint = shapely.union_all(polygons[shapely.area(polygons) > 1e-10])
    assert footprint.is_valid and not footprint.is_empty
    n = tile['samples']; size = cfg['texture_size']; spacing = tile['xy_scale_cm']/100
    assert size >= n and size & (size-1) == 0
    origin = np.array(tile['bounds_xy_cm'][:2])/100
    lo = np.maximum(0, np.floor((np.array(footprint.bounds[:2])-cfg['feather_m']-origin)/spacing).astype(int))
    hi = np.minimum(n-1, np.ceil((np.array(footprint.bounds[2:])+cfg['feather_m']-origin)/spacing).astype(int))
    yy, xx = np.mgrid[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
    points = shapely.points(origin[0]+xx.ravel()*spacing, origin[1]+yy.ravel()*spacing)
    distances = shapely.distance(points, footprint)
    fade = np.clip(1-distances/cfg['feather_m'], 0, 1)
    fade = fade*fade*(3-2*fade)
    mask = np.zeros((size, size), np.uint8)
    holes = np.frombuffer(Path(tile['holes']).read_bytes(), dtype=np.uint8).reshape(n, n)
    patch = np.rint(fade.reshape(xx.shape)*255).astype(np.uint8)
    # In this project zero is a valid Landscape vertex, 255 denotes a hole.
    patch[holes[lo[1]:hi[1]+1, lo[0]:hi[0]+1] != 0] = 0
    mask[lo[1]:hi[1]+1, lo[0]:hi[0]+1] = patch
    assert np.count_nonzero(mask) > 0
    folder.mkdir(parents=True); draft.mkdir(parents=True)
    image_path = folder/'bank_mask.png'; Image.fromarray(mask).save(image_path)
    npy = np.flatnonzero(mask)
    audit = {'passed': True, 'build_id': build, 'source_mesh_sha256': sha(record['source']),
             'footprint_area_m2': footprint.area, 'mask_nonzero_samples': int(len(npy)),
             'nonzero_sample_max_distance_from_footprint_m': float(max(distances[patch.ravel() > 0], default=0)),
             'native_sample_spacing_m': spacing, 'texture_size': size, 'mask_sha256': sha(image_path),
             'bilinear_filter_additional_influence_bound_m': spacing*2**0.5,
             'boundary_note': 'Mask texels follow the net mesh XY footprint plus declared feather. Bilinear filtering and lower mip levels have additional sampling footprints; the mask is not a measured rock exposure polygon.',
             'no_height_hole_mesh_or_route_changes': True}
    (draft/'bank_surface_mask_audit.json').write_text(json.dumps(audit, indent=2))
    m = copy.deepcopy(original); m['build_id'] = build
    changed = next(t for t in m['tiles'] if t['id'] == cfg['tile'])
    changed['surface_parent_map'] = changed['map']
    changed['map'] = '/Game/World/Driving/S_'+build+'/Terrain/'+changed['id']
    m['bank_surface'] = {'parent_build_id': original['build_id'], 'parent_manifest': str(original_path),
        'parent_draft': str(parent), 'input_sha256': signatures, 'config': cfg,
        'mask_file': str(image_path), 'mask_sha256': sha(image_path),
        'material_asset': '/Game/World/Driving/S_'+build+'/Materials/M_ObservedRockMoss',
        'texture_asset': '/Game/World/Driving/S_'+build+'/Materials/T_BankMask',
        'geometry_and_physics_changed': False, 'artistic_quality_approved': False}
    m['report'].update(build_id=build, native_imported=False, full_lap_driven=False)
    manifest = folder/'manifest.json'; manifest.write_text(json.dumps(m, indent=2))
    world = json.loads((parent/'circuit_driving_world.json').read_text()); world['build_id'] = build
    for t in world['tiles']:
        if t['id'] == changed['id']: t['map'] = changed['map']
    (draft/'circuit_driving_world.json').write_text(json.dumps(world))
    route = json.loads((parent/'circuit_itinerary.json').read_text()); route['build_id'] = build
    (draft/'circuit_itinerary.json').write_text(json.dumps(route))
    views = json.loads((ROOT/'parameters/bank_views_fd61ea1aa8c4_v1.json').read_text())
    views.update(build_id=build, status='Local procedural surface diagnostic at the two previously reviewed road-aligned viewpoints. No final art or whole-lap acceptance.')
    (draft/'surface_review_views.json').write_text(json.dumps(views, indent=2))
    # Independently compare every inherited record before accepting preparation.
    assert m['meshes'] == original['meshes']
    for a, b in zip(m['tiles'], original['tiles']):
        assert {k: v for k, v in a.items() if k not in ['map', 'surface_parent_map']} == {k: v for k, v in b.items() if k != 'map'}
    result = {'build_id': build, 'parent_build_id': original['build_id'], 'manifest': str(manifest),
              'draft': str(draft), 'change_kind': 'local_procedural_observed_bank_material',
              'changed_tiles': [changed['id']], 'geometry_changed': False, 'activated': False}
    (draft/'structure_preparation.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
