"""Full native-grid coverage masks with type-specific plant envelope exclusions."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from pyproj import Transformer
import shapely

ROOT = Path(__file__).resolve().parents[1]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_geometry(path, geometry):
    path.write_text(json.dumps(shapely.geometry.mapping(geometry), separators=(',', ':')))


def source_groups(config, manifest):
    projection = Transformer.from_crs(4326, 6708, always_xy=True)
    origin = manifest['origin_ENH_m']; features = {}; consumed = set(); inputs = []
    for name in config['sources']:
        folder = ROOT/name
        provenance = json.loads((folder/'provenance.json').read_text())
        assert sha(folder/'cover.geojson') == provenance['geojson_sha256']
        assert sha(folder/'response.json') == provenance['response_sha256']
        collection = json.loads((folder/'cover.geojson').read_text())
        relations = {int(f['id'].split('/')[1]) for f in collection['features'] if f['id'].startswith('relation/')}
        response = json.loads((folder/'response.json').read_text())
        for e in response['elements']:
            if e['type'] == 'relation' and e['id'] in relations:
                consumed.update(v['ref'] for v in e.get('members', []) if v['type'] == 'way' and v.get('role', '') in ['', 'outer', 'inner'])
        features.update({f['id']: f for f in collection['features']})
        inputs += [folder/k for k in ['provenance.json', 'response.json', 'cover.geojson']]
    groups = {k: [] for k in ['forest', 'scrub', 'meadow', 'buildings', 'roads', 'paths', 'streams', 'water', 'power']}
    for key, feature in features.items():
        if key.startswith('way/') and int(key.split('/')[1]) in consumed: continue
        tags = feature['properties']; geometry = shapely.geometry.shape(feature['geometry'])
        if geometry.geom_type == 'LineString' and geometry.is_closed and (tags.get('building') or tags.get('waterway') in ['riverbank', 'dock']):
            geometry = shapely.Polygon(geometry.coords)
        geometry = shapely.transform(geometry, projection.transform, interleaved=False)
        geometry = shapely.transform(geometry, lambda p: np.c_[p[:, 0]-origin[0], origin[1]-p[:, 1]])
        if not geometry.is_valid: geometry = shapely.make_valid(geometry)
        polygon = geometry.geom_type in ['Polygon', 'MultiPolygon']
        if polygon and (tags.get('landuse') == 'forest' or tags.get('natural') == 'wood'): groups['forest'].append(geometry)
        if polygon and tags.get('natural') == 'scrub': groups['scrub'].append(geometry)
        if polygon and (tags.get('landuse') in ['meadow', 'grass'] or tags.get('natural') == 'grassland'): groups['meadow'].append(geometry)
        if tags.get('building'): groups['buildings'].append(geometry)
        if tags.get('natural') == 'water' or tags.get('landuse') in ['reservoir', 'basin'] or tags.get('waterway') in ['riverbank', 'dock']:
            groups['water'].append(geometry)
        elif tags.get('waterway'): groups['streams'].append(geometry)
        if tags.get('power') in ['line', 'minor_line']: groups['power'].append(geometry)
        if tags.get('highway'):
            name = 'paths' if tags['highway'] in ['footway', 'path', 'steps', 'cycleway', 'bridleway'] else 'roads'
            groups[name].append(geometry)
    return {k: shapely.union_all(v) for k, v in groups.items()}, {k: len(v) for k, v in groups.items()}, inputs


def native_missing(holes):
    padded = np.pad(holes != 0, 1, mode='edge'); n = len(holes)
    return np.logical_or.reduce([padded[y:y+n, x:x+n] for x in range(3) for y in range(3)])


def main():
    p = argparse.ArgumentParser(); p.add_argument('--parent-manifest', type=Path, required=True)
    p.add_argument('--config', type=Path, required=True); args = p.parse_args()
    m = json.loads(args.parent_manifest.read_text()); cfg = json.loads(args.config.read_text())
    groups, feature_counts, inputs = source_groups(cfg, m)
    inputs += [args.parent_manifest, args.config, Path(__file__)]
    for r in m['meshes']: inputs.append(Path(r['source']))
    for t in m['tiles']: inputs += [Path(t['heightmap']), Path(t['holes'])]
    signatures = {str(p.resolve()): sha(p) for p in inputs}
    build = hashlib.sha256(json.dumps(signatures, sort_keys=True).encode()).hexdigest()[:12]
    folder = ROOT/'terrain/world_vegetation_masks'/build
    if folder.exists(): raise RuntimeError('Preserve previous mask generation')
    folder.mkdir(parents=True)
    plan = []
    for r in m['meshes']:
        data = json.loads(Path(r['source']).read_text())
        vertices = (np.array(data['vertices_cm'])+r['location_cm'])/100
        faces = vertices[np.array(data['triangles']), :2]
        polygons = shapely.polygons(faces); polygons = polygons[shapely.area(polygons) > 1.e-10]
        if len(polygons): plan.append(shapely.union_all(polygons))
    built = shapely.union_all(plan)
    base = shapely.union_all([built, groups['roads'].buffer(cfg['mapped_road_half_width_m']),
        groups['paths'].buffer(cfg['mapped_path_half_width_m']), groups['buildings'].buffer(cfg['building_extra_clearance_m']),
        groups['streams'].buffer(cfg['stream_half_width_m']), groups['water'].buffer(cfg['water_extra_clearance_m']),
        groups['power'].buffer(cfg['power_corridor_half_width_m'])])
    write_geometry(folder/'base_exclusions.geojson', base)
    for name in ['forest', 'scrub', 'meadow']: write_geometry(folder/(name+'.geojson'), groups[name])
    step = m['tiles'][0]['xy_scale_cm']/100
    exclusions = {b['id']: base.buffer(b['plant_radius_m']+step/np.sqrt(2)+cfg['sampling_guard_m']) for b in cfg['branches']}
    for name, g in exclusions.items(): write_geometry(folder/(name+'_exclusions.geojson'), g); shapely.prepare(g)
    for name in ['forest', 'scrub', 'meadow']: shapely.prepare(groups[name])
    totals = {b['id']: 0 for b in cfg['branches']}; records = []
    for tile in m['tiles']:
        n = tile['samples']; spacing = tile['xy_scale_cm']/100; origin = np.array(tile['bounds_xy_cm'][:2])/100
        x, y = np.meshgrid(origin[0]+np.arange(n)*spacing, origin[1]+np.arange(n)*spacing)
        cover = np.zeros((n, n), 'u1')
        for name, code in [('forest', 1), ('scrub', 3), ('meadow', 2)]:
            cover[shapely.intersects_xy(groups[name], x, y)] = code
        holes = np.fromfile(tile['holes'], 'u1').reshape(n, n); missing = native_missing(holes)
        cover[missing] = 0
        cover_file = folder/(tile['id']+'_cover.bin'); cover.tofile(cover_file)
        row = {'tile': tile['id'], 'width': n, 'height': n, 'spacing_cm': tile['xy_scale_cm'], 'origin_cm': [*tile['bounds_xy_cm'][:2], 0],
               'cover_file': str(cover_file), 'cover_sha256': sha(cover_file),
               'source_height_sha256': tile['height_sha256'], 'source_holes_sha256': tile['holes_sha256'], 'branches': {}}
        for b in cfg['branches']:
            allowed = np.isin(cover, b['cover_classes']) & ~shapely.intersects_xy(exclusions[b['id']], x, y)
            allowed[-1, :] = False; allowed[:, -1] = False
            path = folder/(tile['id']+'_'+b['id']+'.bin'); allowed.astype('u1').tofile(path)
            count = int(allowed.sum()); totals[b['id']] += count
            row['branches'][b['id']] = {'mask_file': str(path), 'mask_sha256': sha(path), 'allowed_cells': count}
        if any(v['allowed_cells'] for v in row['branches'].values()):
            palette = np.array([[85, 82, 75], [42, 95, 40], [169, 176, 86], [102, 137, 60]], 'u1')
            preview = palette[cover]; preview[shapely.intersects_xy(base, x, y)] = [165, 66, 58]
            Image.fromarray(preview).resize((505, 505), Image.Resampling.NEAREST).save(folder/(tile['id']+'_cover.png'))
        records.append(row); print('WORLD_MASK '+tile['id']+' '+str({k: v['allowed_cells'] for k, v in row['branches'].items()}), flush=True)
    result = {'mask_build_id': build, 'parent_build_id': m['build_id'], 'parent_manifest': str(args.parent_manifest.resolve()),
              'config': cfg, 'input_sha256': signatures, 'mapped_feature_counts': feature_counts, 'tiles': records, 'allowed_cells_per_branch': totals,
              'source_geometry': {name: str(folder/(name+'.geojson')) for name in ['forest', 'scrub', 'meadow']},
              'base_exclusions': str(folder/'base_exclusions.geojson'),
              'branch_exclusions': {b['id']: str(folder/(b['id']+'_exclusions.geojson')) for b in cfg['branches']},
              'native_pcg_executed': False, 'tree_positions_observed': False, 'species_observed': False,
              'scope': 'All 113 native grids, mapped cover and conservative envelope exclusions. Unknown cover stays empty. These are PCG input masks, not spawned vegetation or a complete habitat survey.',
              'license': 'ODbL-1.0, OpenStreetMap contributors; https://www.openstreetmap.org/copyright'}
    output = folder/'manifest.json'; output.write_text(json.dumps(result, indent=2)); print('WORLD_MASK_MANIFEST '+str(output), flush=True)


if __name__ == '__main__': main()
