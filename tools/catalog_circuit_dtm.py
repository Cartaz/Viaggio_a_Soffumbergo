"""Validate the user's full-circuit ASCII tiles and sample the OSM candidate.

Raster originals are read only. Catalog/statistics can be reviewed for publication;
sampled ground geometry stays under build/, never promoted to verified asphalt.
"""
import argparse
import json
import math
from pathlib import Path
import re

from coffa.terrain import sample_grid
from register_dtm import sha256_file

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826'


def read_header(stream):
    header = {}
    for _ in range(6):
        parts = stream.readline().split()
        if len(parts) != 2 or parts[0].lower() in header:
            raise ValueError('Malformed/duplicate ASC header')
        header[parts[0].lower()] = float(parts[1])
    if set(header) != {'ncols', 'nrows', 'xllcenter', 'yllcenter', 'cellsize', 'nodata_value'}:
        raise ValueError('Expected the cell-centre header of the received FVG collection')
    if any(not math.isfinite(v) for v in header.values()):
        raise ValueError('Nonfinite header')
    if (header['ncols'], header['nrows'], header['cellsize'], header['nodata_value']) != (1800, 1680, .5, -9999):
        raise ValueError('Wrong dimensions, resolution or NoData sentinel')
    for field in ['xllcenter', 'yllcenter']:
        if (header[field]-.25) % .5:
            raise ValueError('Misaligned cell centres')
    return header


def overlap_slices(a, b):
    """Return row/col slices for identical sample centres, or None for no overlap."""
    ax, ay, ar, at = a
    bx, by, br, bt = b
    west, south, east, north = max(ax, bx), max(ay, by), min(ar, br), min(at, bt)
    if west >= east or south >= north:
        return None
    if any(abs(v/.5-round(v/.5)) > 1e-7 for v in [west-ax, west-bx, at-north, bt-north]):
        raise ValueError('Tiles do not share the same cell-centre lattice')
    def window(x, top):
        return (slice(round((top-north)/.5), round((top-south)/.5)),
                slice(round((west-x)/.5), round((east-x)/.5)))
    return window(ax, at), window(bx, bt)


def resolve_samples(candidates):
    """Never average conflicting observed samples; epsilon only absorbs roundoff."""
    if not candidates:
        return None, 'uncovered', None
    if any(not math.isfinite(h) for h in candidates):
        raise ValueError('Nonfinite sampled height')
    spread = max(candidates)-min(candidates)
    if spread > 1e-6:
        return None, 'conflicting_overlap', spread
    return candidates[0], 'covered', spread


def run(input_dir, output, crs, vertical):
    import numpy as np
    from pyproj import Transformer, network
    network.set_network_enabled(False)
    if not output.resolve().is_relative_to(ROOT/'build'):
        raise ValueError('Ground-derived geometry must stay under build/')
    files = sorted(input_dir.glob('*.asc'))
    if not files:
        raise ValueError('No ASCII tiles found')
    tiles, arrays = [], []
    for index, path in enumerate(files):
        if not re.fullmatch(r'Ell_DTM_\d{8}\.asc', path.name):
            raise ValueError('Unrecognized tile name: '+path.name)
        with path.open('r', encoding='ascii') as stream:
            h = read_header(stream)
            values = np.loadtxt(stream, dtype=np.float32)
        if values.shape != (1680, 1800) or not np.isfinite(values).all():
            raise ValueError('Corrupt or nonfinite grid: '+path.name)
        valid = values != -9999
        if not valid.any():
            raise ValueError('Empty grid: '+path.name)
        west, south = h['xllcenter']-.25, h['yllcenter']-.25
        tile = {'filename': path.name, 'sha256': sha256_file(path), 'bytes': path.stat().st_size,
                'bounds_EN_m': [west, south, west+900, south+840], 'ncols': 1800, 'nrows': 1680,
                'resolution_m': .5, 'valid_cells': int(valid.sum()), 'nodata_cells': int((~valid).sum()),
                'minimum_declared_ellipsoidal_height_m': float(values[valid].min()),
                'maximum_declared_ellipsoidal_height_m': float(values[valid].max())}
        tiles.append(tile)
        arrays.append(values)
        print(f'Read {index+1}/{len(files)}: {path.name}', flush=True)
    overlaps = []
    for i, a in enumerate(tiles):
        for j, b in enumerate(tiles[:i]):
            windows = overlap_slices(a['bounds_EN_m'], b['bounds_EN_m'])
            if windows is None:
                continue
            left, right = arrays[i][windows[0]], arrays[j][windows[1]]
            valid = (left != -9999) & (right != -9999)
            error = float(np.max(np.abs(left[valid]-right[valid]))) if valid.any() else None
            overlaps.append({'a': a['filename'], 'b': b['filename'],
                             'compared_valid_cells': int(valid.sum()), 'max_difference_m': error,
                             'different_cells': int(np.count_nonzero(left[valid] != right[valid]))})
    route_path = ROOT/'data/geography/circuito_osm_candidate_20261020.geojson'
    route = json.loads(route_path.read_text(encoding='utf-8'))
    project = Transformer.from_crs('EPSG:4326', crs, always_xy=True, allow_ballpark=False)

    def sample(east, north):
        candidates = []
        for tile, values in zip(tiles, arrays):
            west, south, right, top = tile['bounds_EN_m']
            if west+.25 <= east <= right-.25 and south+.25 <= north <= top-.25:
                try:
                    candidates.append(sample_grid(values, east, north, west, top))
                except ValueError:
                    continue
        return resolve_samples(candidates)

    profiles, coverage = [], []
    origin = [375920, 5112728, 720]
    for feature in route['features']:
        sector = feature['properties']['sector']
        coords = [project.transform(*p[:2]) for p in feature['geometry']['coordinates']]
        points = [coords[0]]
        for a, b in zip(coords, coords[1:]):
            count = max(1, math.ceil(math.dist(a, b)/2))
            points.extend([(a[0]+i/count*(b[0]-a[0]), a[1]+i/count*(b[1]-a[1])) for i in range(1,count+1)])
        samples, missing, conflicts, all_heights = [], [], [], []
        for e, n in points:
            height, status, spread = sample(e, n)
            if status == 'uncovered':
                missing.append([round(e, 3), round(n, 3)])
            elif status == 'conflicting_overlap':
                conflicts.append({'EN_m': [round(e, 3), round(n, 3)], 'height_spread_m': spread})
            else:
                all_heights.append(height)
            samples.append(None if height is None else [e-origin[0], height-origin[2], origin[1]-n])
        heights = all_heights
        coverage.append({'sector': sector, 'samples_at_max_2m_spacing': len(samples),
                         'geographically_covered_samples': len(samples)-len(missing),
                         'unambiguous_height_samples': len(heights),
                         'conflicting_height_samples': len(conflicts), 'uncovered_samples': len(missing),
                         'uncovered_EN_m_first_20': missing[:20],
                         'conflicting_EN_m_first_20': conflicts[:20],
                         'max_overlap_height_spread_on_route_m': max((c['height_spread_m'] for c in conflicts), default=0),
                         'minimum_ground_height_m': min(heights) if heights else None,
                         'maximum_ground_height_m': max(heights) if heights else None})
        profiles.append({'sector': sector, 'points_local_m': samples})
    output.mkdir(parents=True, exist_ok=True)
    (ROOT/'build/.gdignore').touch()
    catalog = {'schema_version': 1, 'dataset_source': SOURCE,
               'acquisition': 'user-supplied DTM Completi, 2026-10-20',
               'horizontal_crs_operator_declared': crs,
               'horizontal_metadata_verified_per_tile': False,
               'georeferencing_basis': 'Same named collection; four Valle rasters match prior verified SHA256; ASCII has no embedded CRS',
               'vertical_reference_operator_declared': vertical,
               'vertical_metadata_verified_independently': False,
               'datum_conversion_applied': False, 'raw_rasters_committed': False,
               'source_license_for_redistribution': 'pending regional metadata rights review',
               'tile_count': len(tiles), 'total_source_bytes': sum(t['bytes'] for t in tiles),
               'total_input_cells': sum(t['valid_cells']+t['nodata_cells'] for t in tiles),
               'total_nodata_cells': sum(t['nodata_cells'] for t in tiles),
               'tiles': tiles, 'overlaps': overlaps, 'route_source_sha256': sha256_file(route_path),
               'overlap_pairs_with_differences': sum(o['different_cells'] > 0 for o in overlaps),
               'max_overlap_difference_m': max((o['max_difference_m'] or 0 for o in overlaps), default=0),
               'mosaic_merge_performed': False,
               'conflict_policy': 'No first-tile priority or averaging; ambiguous route heights remain null',
               'route_status': route['route_status'], 'route_ground_coverage': coverage,
               'route_ground_fully_covered_at_2m': all(c['uncovered_samples'] == 0 for c in coverage),
               'route_height_unambiguous_at_2m': all(c['conflicting_height_samples'] == 0 for c in coverage),
               'road_surface_verified': False,
               'coverage_scope': 'Samples of OSM candidate only, not road widths, corridor or verified turns'}
    (output/'dtm_catalog.json').write_text(json.dumps(catalog, indent=2)+'\n', encoding='utf-8')
    (output/'route_ground_candidate.json').write_text(json.dumps(
        {'origin_ENH_m': origin, 'axes': '+X east, +Y up, +Z south',
         'status': 'DTM_ground_only_not_verified_asphalt_or_driving_route',
         'profiles': profiles}, separators=(',', ':'), allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps({k:catalog[k] for k in ['tile_count','total_source_bytes','total_input_cells',
                      'total_nodata_cells','max_overlap_difference_m','overlap_pairs_with_differences',
                      'route_ground_fully_covered_at_2m','route_height_unambiguous_at_2m','route_ground_coverage']}, indent=2))
    return catalog


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'build/circuit_dtm')
    parser.add_argument('--horizontal-crs', choices=['EPSG:6708'], required=True)
    parser.add_argument('--vertical-datum', choices=['ellipsoidal'], required=True)
    args = parser.parse_args()
    run(args.input_dir, args.output_dir, args.horizontal_crs, args.vertical_datum)
