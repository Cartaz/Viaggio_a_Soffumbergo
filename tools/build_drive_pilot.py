"""Create a declared engineering trial, NOT a surveyed road, on the last ~600m of C.

Original DTM and circuit manifest are immutable inputs. Runtime-only terrain
grading is recorded as an approximation; it does not resolve real road geometry.
"""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from build_circuit_3d import encode, atomic_write

ROOT = Path(__file__).resolve().parents[1]


def closest(points, x, z):
    """Vectorized closest horizontal station, interpolated design height and distance."""
    points = np.asarray(points, dtype=float)
    shape = np.broadcast_arrays(x, z)[0].shape
    query = np.column_stack([np.asarray(x).ravel(), np.asarray(z).ravel()])
    a, delta = points[:-1, [0, 2]], np.diff(points[:, [0, 2]], axis=0)
    den = (delta*delta).sum(axis=1)
    if np.any(den < 1e-10):
        raise ValueError('Duplicate horizontal station')
    t = np.clip(((query[:, None, :]-a)*delta).sum(axis=2)/den, 0, 1)
    dist2 = ((query[:, None, :]-a-t[:, :, None]*delta)**2).sum(axis=2)
    ids = dist2.argmin(axis=1)
    j = np.arange(len(query))
    heights = points[ids, 1]+t[j, ids]*(points[ids+1, 1]-points[ids, 1])
    return np.sqrt(dist2[j, ids]).reshape(shape), heights.reshape(shape)


def smooth_profile(points, radius=12):
    """Local linear fit preserves grades, including endpoints; no claim of measured asphalt."""
    p = np.asarray(points, dtype=float)
    station = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p[:, [0, 2]], axis=0), axis=1))]
    result = p.copy()
    for i, s in enumerate(station):
        mask = np.abs(station-s) <= radius
        a = np.column_stack([np.ones(mask.sum()), station[mask]-s])
        result[i, 1] = np.linalg.lstsq(a, p[mask, 1], rcond=None)[0][0]+.15
    return result


def make_strip(points, width):
    if not math.isfinite(width) or width <= 0:
        raise ValueError('Invalid test width')
    p = np.asarray(points, dtype=float)
    direction = np.roll(p[:, [0, 2]], -1, axis=0)-np.roll(p[:, [0, 2]], 1, axis=0)
    direction[0] = p[1, [0, 2]]-p[0, [0, 2]]
    direction[-1] = p[-1, [0, 2]]-p[-2, [0, 2]]
    direction /= np.linalg.norm(direction, axis=1)[:, None]
    right = np.column_stack([-direction[:, 1], np.zeros(len(p)), direction[:, 0]])
    vertices = np.stack([p-right*width/2, p+right*width/2], axis=1).reshape(-1, 3)
    # 1m test end aprons keep exact endpoint rays away from mesh boundaries.
    vertices[:2] -= (p[1]-p[0])/np.linalg.norm(p[1,[0,2]]-p[0,[0,2]])
    vertices[-2:] += (p[-1]-p[-2])/np.linalg.norm(p[-1,[0,2]]-p[-2,[0,2]])
    triangles = [[k-2, k, k-1] for k in range(2, len(vertices), 2)]
    triangles += [[k-1, k, k+1] for k in range(2, len(vertices), 2)]
    # Godot clockwise fronts; reject a folded or degenerate join.
    faces = vertices[np.asarray(triangles)]
    if np.any(np.cross(faces[:, 1]-faces[:, 0], faces[:, 2]-faces[:, 0])[:, 1] >= -1e-8):
        raise ValueError('Folded trial road; requires manual engineering')
    return vertices.tolist(), triangles


def main():
    folder = ROOT/'build/circuit'
    original_bytes = (folder/'manifest.json').read_bytes()
    manifest = json.loads(original_bytes)
    route_bytes = (ROOT/'data/geography/circuito_osm_candidate_20261020.geojson').read_bytes()
    raw = manifest['route'][2]['points_m']
    distance, first = 0, len(raw)-1
    while first > 0 and distance < 600:
        distance += math.dist(raw[first], raw[first-1])
        first -= 1
    points = smooth_profile(raw[first:])
    width = 4.5  # Operator test parameter, explicitly not an observed carriageway width.
    vertices, triangles = make_strip(points, width)
    source = hashlib.sha256(original_bytes).hexdigest()
    build_id = hashlib.sha256(encode({'source':source,'generator':hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest()})).hexdigest()[:20]
    entries = {tuple(e['offset_xz_m']):e for e in manifest['sectors']}
    cache = {}

    def chunk(key):
        if key not in cache:
            e = entries[key]
            b = (folder/e['path']).read_bytes()
            if hashlib.sha256(b).hexdigest() != e['sha256']:
                raise ValueError('Changed source chunk')
            cache[key] = json.loads(b)
        return cache[key]

    def base_height(x, z):
        key = (math.floor(x/128)*128, math.floor(z/128)*128)
        if key not in entries:
            candidates = [(key[0]-128,key[1]),(key[0],key[1]-128),(key[0]-128,key[1]-128)]
            key = next((k for k in candidates if k in entries and 0 <= x-k[0] <= 128 and 0 <= z-k[1] <= 128),None)
            if key is None:
                raise ValueError('Missing halo coverage')
        data = chunk(key)
        return data['heights_m'][round((z-key[1])/2)*65+round((x-key[0])/2)]

    def graded(x, z):
        dist, level = closest(points, x, z)
        values = np.array([base_height(a, b) for a, b in zip(x.ravel(), z.ravel())]).reshape(x.shape)
        if not np.isfinite(values).all():
            raise ValueError('Missing terrain; no invented fill allowed')
        t = np.clip((dist-width/2-1)/8, 0, 1)
        blend = 1-t*t*(3-2*t)
        return values+(level-.35-values)*blend

    changed, max_cut_fill = 0, 0.0
    max_step = 0.0
    for e in manifest['sectors']:
        ox, oz = e['offset_xz_m']
        x,z = np.meshgrid(ox+np.arange(65)*2, oz+np.arange(65)*2)
        dist,_ = closest(points, x, z)
        if float(dist.min()) > width/2+12:
            continue
        d = json.loads(json.dumps(chunk((ox, oz))))
        old = np.array(d['heights_m']).reshape(65,65)
        new = graded(x, z)
        max_cut_fill = max(max_cut_fill, float(np.abs(new-old).max()))
        normals = np.array(d['normals']).reshape(65,65,3)
        mask = dist <= width/2+12
        xx,zz = x[mask],z[mask]
        n = np.column_stack([-(graded(xx+2,zz)-graded(xx-2,zz))/4, np.ones(len(xx)), -(graded(xx,zz+2)-graded(xx,zz-2))/4])
        n /= np.linalg.norm(n,axis=1)[:,None]
        normals[mask] = n
        d['heights_m'] = np.round(new,6).ravel().tolist()
        d['normals'] = np.round(normals,6).reshape(-1,3).tolist()
        d['engineering_trial_grading'] = True
        encoded = encode(d)
        e['path'] = f'datasets/drive_{build_id}/{d["id"]}.json'
        e['sha256'] = hashlib.sha256(encoded).hexdigest()
        e['overview']['heights_m'] = np.round(new[::4,::4],6).ravel().tolist()
        e['overview']['normals'] = np.round(normals[::4,::4],6).reshape(-1,3).tolist()
        atomic_write(folder/e['path'], encoded)
        changed += 1
    # Shared engineering changes must match across both affected and unchanged sectors.
    checked = 0
    for key,e in entries.items():
        if not e['path'].startswith('datasets/drive_'):
            continue
        d = json.loads((folder/e['path']).read_bytes())
        for dx,dz in [(128,0),(0,128)]:
            neighbor = entries.get((key[0]+dx,key[1]+dz))
            if neighbor:
                other = json.loads((folder/neighbor['path']).read_bytes())
                for i in range(65):
                    a,b = (i*65+64,i*65) if dx else (64*65+i,i)
                    max_step = max(max_step,abs(d['heights_m'][a]-other['heights_m'][b]))
                checked += 1
    if max_step > 1e-5:
        raise ValueError('Trial terrain seam changed')
    manifest['engineering_trial'] = {'status':'not_surveyed_road','original_manifest_sha256':source}
    atomic_write(folder/'pilot_manifest.json',encode(manifest))
    delta = np.diff(points,axis=0)
    grades = np.abs(delta[:,1]/np.linalg.norm(delta[:,[0,2]],axis=1))
    road = {'schema_version':1,'prototype':'Valle driving trial 0.1','status':'engineering_trial_not_surveyed_road',
            'axes':manifest['axes'],'horizontal_crs':manifest['horizontal_crs'],'origin_ENH_m':manifest['origin_ENH_m'],
            'source_manifest_sha256':source,'candidate_sha256':hashlib.sha256(route_bytes).hexdigest(),
            'sector':'C','source_point_range':[first,len(raw)-1],'points_m':points.tolist(),
            'vertices_m':vertices,'triangles':triangles,'width_m':width,'width_status':'test_parameter_not_measured',
            'crossfall_status':'zero_design_assumption','vertical_status':'12m_local_linear_fit_DTM_plus_0.15m_not_measured_asphalt',
            'end_apron_horizontal_extension_m':1.0,
            'terrain_status':'local_engineering_grading_only_originals_unchanged','max_trial_cut_fill_m':max_cut_fill,
            'graded_sectors':changed,'checked_trial_edges':checked,'max_trial_edge_error_m':max_step,
            'length_3d_m':float(np.linalg.norm(delta,axis=1).sum()),'max_design_grade':float(grades.max()),
            'max_design_center_delta_from_DTM_m':float(np.abs(points[:,1]-np.array(raw[first:])[:,1]).max()),
            'real_junctions_verified':False,'real_road_surface_verified':False,
            'scope':'Reach the north entrance candidate, not PV-01 or the village visit'}
    atomic_write(folder/'pilot_road.json',encode(road))
    report = {k:v for k,v in road.items() if k not in ['points_m','vertices_m','triangles']}
    atomic_write(folder/'pilot_generation_report.json',encode(report))
    assert (folder/'manifest.json').read_bytes() == original_bytes
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
