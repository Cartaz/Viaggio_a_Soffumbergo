#!/usr/bin/env python3
"""Regenerate Valle 3D 0.1 locally from the checksum-verified user archive.

All terrain-derived output stays under ignored build/ (rights review pending).
OSM source IDs and placeholder dimensions travel with every generated feature.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

from coffa.terrain import clip_segment, lod_grid_error, sample_grid
from import_valle_lidar05 import read_grids, mosaic

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as fh:
        return hashlib.file_digest(fh, 'sha256').hexdigest()


def generate(source, output, config_path=ROOT / 'data/config/valle_3d.json'):
    from pyproj import Transformer, network
    # No unrecorded network grids or guessed orthometric transformation.
    network.set_network_enabled(False)
    projection = Transformer.from_crs('EPSG:4326', 'EPSG:6708', always_xy=True,
                                      allow_ballpark=False)
    config = json.loads(config_path.read_text(encoding='utf-8'))
    output = output.resolve()
    if not output.is_relative_to(ROOT / 'build'):
        raise ValueError('Generated terrain must stay under ignored build/ pending rights review')
    (ROOT/'build').mkdir(exist_ok=True)
    (ROOT/'build/.gdignore').touch()
    terrain, repeats = mosaic(read_grids(source)[0])
    east, north, datum = config['origin_ENH_m']
    xmin, zmin, xmax, zmax = config['region_local_xz_m']
    size, step = config['sector_size_m'], config['terrain_step_m']
    if size != 128 or step != 2 or config['lod_strides'] != [1, 2, 4]:
        raise ValueError('Unsupported sector/LOD configuration')
    if any(v % size for v in (xmin, zmin, xmax, zmax)) or xmin >= xmax or zmin >= zmax:
        raise ValueError('Region must contain whole aligned sectors')

    def height(x, z):
        return sample_grid(terrain, east+x, north-z, 375240, 5113365) - datum

    def local(c):
        e, n = projection.transform(c[0], c[1])
        return [e-east, north-n]

    sectors = []
    for z in range(zmin, zmax, size):
        for x in range(xmin, xmax, size):
            side = size // step + 1
            heights, normals = [], []
            for r in range(side):
                for c in range(side):
                    px, pz = x+c*step, z+r*step
                    heights.append(round(height(px, pz), 4))
                    dx = (height(px+.5, pz)-height(px-.5, pz))
                    dz = (height(px, pz+.5)-height(px, pz-.5))
                    norm = math.sqrt(dx*dx+1+dz*dz)
                    normals.append([round(-dx/norm, 6), round(1/norm, 6), round(-dz/norm, 6)])
            errors = [lod_grid_error(heights, side, s) for s in config['lod_strides']]
            sectors.append({'id': f'{x}_{z}', 'offset_xz_m': [x, z], 'side': side,
                            'heights_m': heights, 'normals': normals,
                            'lod_max_error_m': errors, 'skirt_depth_m': max(errors)+1})

    # Drape visual ribbons on the *fixed collision grid*, not on a changing LOD.
    def mesh_height(x, z):
        sx = min(int((x-xmin)//size), (xmax-xmin)//size-1)
        sz = min(int((z-zmin)//size), (zmax-zmin)//size-1)
        sector = sectors[sz*((xmax-xmin)//size)+sx]
        u = (x-sector['offset_xz_m'][0])/step
        v = (z-sector['offset_xz_m'][1])/step
        c, r = min(int(u), side-2), min(int(v), side-2)
        u, v = u-c, v-r
        h = sector['heights_m']
        a, b, d, e = [h[i] for i in (r*side+c, r*side+c+1, (r+1)*side+c, (r+1)*side+c+1)]
        return a+(b-a)*u+(d-a)*v if u+v <= 1 else e+(d-e)*(1-u)+(b-e)*(1-v)

    osm_path = ROOT / 'data/geography/osm_survey.geojson'
    osm = json.loads(osm_path.read_text(encoding='utf-8'))
    buildings, roads, skipped = [], [], []
    for feature in osm['features']:
        tags, geometry = feature['properties'], feature['geometry']
        identity = feature['id']
        url = 'https://www.openstreetmap.org/' + identity
        if 'building' in tags and geometry['type'] == 'Polygon':
            ring = [local(c) for c in geometry['coordinates'][0][:-1]]
            if len(geometry['coordinates']) != 1 or any(not (xmin <= p[0] <= xmax and zmin <= p[1] <= zmax) for p in ring):
                skipped.append({'id': identity, 'reason': 'building_outside_region_or_holes'})
                continue
            base = min(height(*p) for p in ring)-.25
            roof = max(height(*p) for p in ring)+config['building_placeholder_height_m']
            buildings.append({'id': identity, 'source_url': url, 'ring_xz_m': ring,
                              'base_y_m': base, 'roof_y_m': roof,
                              'height_status': config['building_height_status'],
                              'name': tags.get('name', tags.get('building', 'OSM'))})
        if 'highway' not in tags or geometry['type'] != 'LineString':
            continue
        pedestrian = tags['highway'] in ('path', 'footway', 'steps')
        width = config['footpath_placeholder_width_m'] if pedestrian else config['road_placeholder_width_m']
        # Offset both sides after clipping inside a half-width margin.
        margin = width/2+.01
        bounds = [xmin+margin, zmin+margin, xmax-margin, zmax-margin]
        coords = [local(c) for c in geometry['coordinates']]
        for index, (a, b) in enumerate(zip(coords, coords[1:])):
            clipped = clip_segment(a, b, bounds)
            if clipped is None:
                continue
            a, b = clipped
            length = math.dist(a, b)
            if length < .001:
                continue
            count = max(1, math.ceil(length/.5))
            columns = max(1, math.ceil(width/.5)) + 1
            dx, dz = (b[0]-a[0])/length, (b[1]-a[1])/length
            vertices = []
            for i in range(count+1):
                x, z = a[0]+i/count*(b[0]-a[0]), a[1]+i/count*(b[1]-a[1])
                for j in range(columns):
                    offset = (j/(columns-1)-.5)*width
                    px, pz = x+(-dz)*offset, z+dx*offset
                    vertices.append([px, mesh_height(px, pz)+.25, pz])
            roads.append({'id': f'{identity}/{index}', 'source_url': url,
                          'highway': tags['highway'], 'pedestrian': pedestrian,
                          'width_m': width, 'width_status': config['road_width_status'],
                          'status': config['road_surface_status'], 'columns': columns,
                          'vertices_m': vertices})
    anchors = []
    for f in json.loads((ROOT/'data/geography/survey_points.geojson').read_text(encoding='utf-8'))['features']:
        x, z = local(f['geometry']['coordinates'])
        anchors.append({'id': f['id'], 'position_m': [x, height(x, z), z],
                        'status': f['properties']['status'], 'name': f['properties']['name']})
    report = {'schema_version': 1, 'prototype': 'Valle 3D 0.1', 'axes': '+X east, +Y up, +Z south',
              'horizontal_crs': 'EPSG:6708', 'vertical_reference': 'ellipsoidal_as_declared_Ell_DTM',
              'vertical_metadata_verified_independently': False,
              'datum_conversion_applied': False, 'origin_ENH_m': config['origin_ENH_m'],
              'cell_centres_used': True, 'source_zip_sha256': sha(source),
              'osm_sha256': sha(osm_path), 'config_sha256': sha(config_path),
              'overlap_duplicate_cells': repeats, 'ground_only': True,
              'redistribution_status': 'local_only_pending_rights_review',
              'osm_attribution': osm['attribution'], 'projection': projection.description,
              'config': config, 'sectors': sectors, 'buildings': buildings, 'roads': roads,
              'anchors': anchors, 'skipped': skipped}
    output.mkdir(parents=True, exist_ok=True)
    destination = output/'valle_scene.json'
    temp = destination.with_suffix('.tmp')
    temp.write_text(json.dumps(report, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n', encoding='utf-8')
    temp.replace(destination)
    summary = {'source_zip_sha256': report['source_zip_sha256'], 'scene_sha256': sha(destination),
               'sector_count': len(sectors), 'building_count': len(buildings),
               'road_segment_count': len(roads), 'skipped': skipped,
               'fixed_collision_triangles': len(sectors)*(side-1)**2*2,
               'lod_max_error_m': [max(s['lod_max_error_m'][i] for s in sectors) for i in range(3)]}
    (output/'generation_report.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'build/valle')
    args = parser.parse_args()
    generate(args.source, args.output_dir)


if __name__ == '__main__':
    main()
