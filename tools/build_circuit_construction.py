"""Build the entire candidate's editable engineering surface and terrain variant.

Input DTM and inspection/pilot manifests are immutable. All geographic derivatives
stay in ignored build/. No real width, pavement, turning circle or retaining wall
is inferred. Reversals are retained and marked as unresolved route issues.
"""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import shapely
from shapely import box
from build_circuit_3d import encode, atomic_write
from coffa.road_construction import (validate_config, design_profile, SegmentIndex,
                                     road_footprint, triangulate_surface)
from coffa.dtm_mosaic import masked_lod_error

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'data/config/circuit_construction.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = ROOT/'build/circuit'
    source_path = folder/'manifest.json'
    original = source_path.read_bytes()
    manifest = json.loads(original)
    config = json.loads(CONFIG.read_bytes())
    validate_config(config)
    fingerprints = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                    for p in [CONFIG, Path(__file__), ROOT/'tools/coffa/road_construction.py']}
    fingerprints['original_manifest'] = digest(source_path)
    fingerprints['shapely_version'] = shapely.__version__
    fingerprints['geos_version'] = shapely.geos_version_string
    build_id = hashlib.sha256(encode(fingerprints)).hexdigest()[:20]
    profile, raw, station, angles, stats = design_profile(manifest['route'], config['profile_radius_m'],
                                                        config['surface_offset_m'])
    index = SegmentIndex(profile)
    width = config['width_m']
    reach = width/2+config['shoulder_m']+config['blend_m']
    aprons = np.where((angles >= config['corner_apron_min_degrees']) &
                      (angles <= config['corner_apron_max_degrees']))[0]
    footprint = road_footprint(profile, width, aprons, config['corner_apron_radius_m'])
    # Remove micron-scale duplicate/collinear buffer vertices before Jolt's
    # mesh quantization. The axis is untouched; boundary tolerance is 1 mm.
    footprint = footprint.simplify(config['footprint_simplify_m'], preserve_topology=True)
    entries = {tuple(e['offset_xz_m']):e for e in manifest['sectors']}
    cache = {}

    def chunk(key):
        if key not in cache:
            e = entries[key]
            if digest(folder/e['path']) != e['sha256']:
                raise ValueError('Changed input chunk '+e['id'])
            cache[key] = json.loads((folder/e['path']).read_bytes())
        return cache[key]

    def base_values(x, z):
        x, z = np.broadcast_arrays(x, z)
        xx, zz = x.ravel(), z.ravel()
        keys = np.column_stack([np.floor(xx/128)*128, np.floor(zz/128)*128]).astype(int)
        result = np.full(len(xx), np.nan)
        for key in np.unique(keys, axis=0):
            mask = (keys == key).all(axis=1)
            if tuple(key) not in entries:
                continue
            d = chunk(tuple(key))
            ids = np.rint((zz[mask]-key[1])/2).astype(int)*65+np.rint((xx[mask]-key[0])/2).astype(int)
            result[mask] = np.asarray(d['heights_m'], dtype=float)[ids]
        return result.reshape(x.shape)

    def graded(x, z, base=None):
        if base is None:
            base = base_values(x, z)
        axis_distance, level, _ = index.query(x, z, reach+config['corner_apron_radius_m'])
        # Conservative distance to the ideal rounded union, containing the mesh.
        distance = np.maximum(axis_distance-width/2, 0)
        for point in profile[aprons]:
            distance = np.minimum(distance, np.maximum(np.hypot(x-point[0], z-point[2])-config['corner_apron_radius_m'], 0))
        active = distance < config['shoulder_m']+config['blend_m']
        if not np.isfinite(base[active]).all():
            raise ValueError('Missing original height inside earthworks corridor')
        result = base.copy()
        t = np.clip((distance[active]-config['shoulder_m'])/config['blend_m'], 0, 1)
        blend = 1-t*t*(3-2*t)
        result[active] += (level[active]-config['terrain_clearance_m']-base[active])*blend
        return result, active

    road_entries, graded_entries = [], 0
    cut, fill, max_change, modified_cells = 0.0, 0.0, 0.0, 0
    earthworks_issues = []
    for number, (key, entry) in enumerate(entries.items()):
        ox, oz = key
        x, z = np.meshgrid(ox+np.arange(65)*2, oz+np.arange(65)*2)
        distance, _, _ = index.query(x, z, reach+config['corner_apron_radius_m']+3)
        if distance.min() > reach+config['corner_apron_radius_m']+3:
            continue
        source = chunk(key)
        old = np.asarray(source['heights_m'], dtype=float).reshape(65, 65)
        new, active = graded(x, z, old)
        if (distance < reach+config['corner_apron_radius_m']+3).any():
            d = json.loads(json.dumps(source))
            new = np.round(new, 6)
            delta = new-old
            max_change = max(max_change, float(np.nanmax(np.abs(delta))))
            if np.nanmax(np.abs(delta)) > config['earthworks_review_m']:
                r, c = np.unravel_index(np.nanargmax(np.abs(delta)), delta.shape)
                earthworks_issues.append({'kind':'large_earthworks_delta', 'terrain_sector':entry['id'],
                                          'point_m':[float(x[r, c]), float(new[r, c]), float(z[r, c])],
                                          'delta_m':float(delta[r, c]),
                                          'status':'requires_earthworks_and_retaining_structure_review'})
            # One ownership per 2x2 m cell; border rows/columns are excluded.
            cell = np.nanmean(np.stack([delta[:-1, :-1], delta[1:, :-1], delta[:-1, 1:], delta[1:, 1:]]), axis=0)
            cut += float(-cell[cell < 0].sum()*4)
            fill += float(cell[cell > 0].sum()*4)
            modified_cells += int(np.count_nonzero(np.abs(cell) > 1e-6))
            normals = np.asarray(d['normals']).reshape(65, 65, 3)
            affected = distance < reach+config['corner_apron_radius_m']+3
            xx, zz = x[affected], z[affected]
            center = new[affected]
            before_x, _ = graded(xx-2, zz)
            after_x, _ = graded(xx+2, zz)
            before_z, _ = graded(xx, zz-2)
            after_z, _ = graded(xx, zz+2)
            def derivative(before, after):
                return np.where(np.isfinite(before) & np.isfinite(after), (after-before)/4,
                                np.where(np.isfinite(after), (after-center)/2,
                                         np.where(np.isfinite(before), (center-before)/2, 0)))
            n = np.column_stack([-derivative(before_x, after_x), np.ones(len(xx)), -derivative(before_z, after_z)])
            n /= np.linalg.norm(n, axis=1)[:, None]
            normals[affected] = n
            d['heights_m'] = [float(v) if np.isfinite(v) else None for v in new.ravel()]
            d['normals'] = np.round(normals, 6).reshape(-1, 3).tolist()
            errors = [masked_lod_error(d['heights_m'], 65, stride) for stride in [1, 2, 4]]
            d['lod_max_error_m'] = errors
            d['skirt_depth_m'] = max(errors)+1
            d['engineering_construction_grading'] = True
            d['original_chunk_sha256'] = entry['sha256']
            entry['path'] = f'datasets/construction_{build_id}/{d["id"]}.json'
            data = encode(d)
            entry['sha256'] = hashlib.sha256(data).hexdigest()
            entry['overview']['heights_m'] = [float(v) if np.isfinite(v) else None for v in new[::4, ::4].ravel()]
            entry['overview']['normals'] = np.round(normals[::4, ::4], 6).reshape(-1, 3).tolist()
            atomic_write(folder/entry['path'], data)
            graded_entries += 1
        part = footprint.intersection(box(ox, oz, ox+128, oz+128))
        if not part.is_empty and part.area > 1e-8:
            vertices, triangles = triangulate_surface(part, index, config['mesh_max_edge_m'], config['corner_apron_radius_m']+.01)
            if triangles:
                road = {'id':entry['id'], 'vertices_m':vertices, 'triangles':triangles,
                        'status':'engineering_surface_not_surveyed_asphalt'}
                data = encode(road)
                relative = f'datasets/construction_{build_id}/road_{entry["id"]}.json'
                atomic_write(folder/relative, data)
                road_entries.append({'id':entry['id'], 'path':relative, 'sha256':hashlib.sha256(data).hexdigest(),
                                     'vertices':len(vertices), 'triangles':len(triangles), 'area_m2':part.area})
        if number % 35 == 0:
            print(f'Construction: {number+1}/{len(entries)} sectors', flush=True)
    issues = []
    sector_labels = [f['sector'] for f in manifest['route'] for _ in f['points_m'][:-1]]
    for i in np.where(angles >= config['turn_warning_degrees'])[0]:
        issues.append({'kind':'exact_reversal' if angles[i] > 179.99 else 'sharp_candidate_corner',
                       'sector':sector_labels[i], 'station_horizontal_m':float(station[i]),
                       'point_m':profile[i].tolist(), 'turn_degrees':float(angles[i]),
                       'status':'requires_route_review_no_automatic_shortcut'})
    delta = np.diff(profile, axis=0)
    grades = np.abs(delta[:, 1]/np.diff(station))
    for i in np.where((grades >= config['grade_warning']) &
                      np.r_[True, grades[:-1] < config['grade_warning']])[0]:
        issues.append({'kind':'steep_design_grade', 'sector':sector_labels[i],
                       'station_horizontal_m':float(station[i]), 'point_m':profile[i].tolist(),
                       'grade':float(grades[i]), 'status':'requires_vertical_profile_review'})
    issues.extend(earthworks_issues)
    report = {'schema_version':1, 'status':'engineering_workbench_not_approved_circuit',
              'build_id':build_id, 'fingerprints':fingerprints, 'config':config,
              'source_manifest_sha256':hashlib.sha256(original).hexdigest(),
              'route_length_horizontal_m':float(station[-1]), 'route_length_3d_m':float(np.linalg.norm(delta, axis=1).sum()),
              'design_area_m2':float(footprint.area), 'graded_sectors':graded_entries,
              'road_sectors':len(road_entries), 'road_triangles':sum(e['triangles'] for e in road_entries),
              'max_earthworks_delta_m':max_change, 'approx_cut_m3':cut, 'approx_fill_m3':fill,
              'volume_status':'2m_cell_average_estimate_not_quantity_survey', 'modified_cells':modified_cells,
              'max_design_grade':float(grades.max()), 'max_center_delta_from_DTM_m':float(np.abs(profile[:-1, 1]-raw[:, 1]).max()),
              'exact_reversals':sum(i['kind'] == 'exact_reversal' for i in issues),
              'corner_apron_count_in_route':len(aprons),
              'corner_apron_source_stations_m':[float(station[i]) for i in aprons],
              'corner_apron_status':'engineering_widening_not_surveyed_geometry_no_reversal_aprons',
              'issues':issues, **stats, 'real_surface_verified':False, 'full_lap_driven':False,
              'original_rasters_modified':False, 'terrain_original_modified':False}
    manifest['engineering_construction'] = {'report':report, 'road_sectors':road_entries,
                                             'profile_points_m':profile.tolist()}
    atomic_write(folder/'construction_manifest.json', encode(manifest))
    atomic_write(folder/'construction_report.json', encode(report))
    assert source_path.read_bytes() == original
    print(json.dumps({k:v for k, v in report.items() if k not in ['issues', 'fingerprints', 'config']}, indent=2))


if __name__ == '__main__':
    main()
