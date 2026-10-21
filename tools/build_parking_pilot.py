"""Separate, synthetic parking apron at the pilot finish. It is NOT PV-01.

Consumes only existing local derivatives; never writes original DTM or pilot files.
"""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from build_circuit_3d import atomic_write, encode
from build_drive_pilot import closest, make_strip

ROOT = Path(__file__).resolve().parents[1]


def design(road):
    p = np.array(road['points_m'], dtype=float)
    station = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1))]
    if station[-1] < 600:
        raise ValueError('Expected the registered 601m pilot approach')
    start, end = 550.0, 582.0
    y0 = np.interp(start, station, p[:, 1])
    level = np.interp(580, station, p[:, 1])
    slope = (np.interp(start+1, station, p[:, 1])-np.interp(start-1, station, p[:, 1]))/2
    t = np.clip((station-start)/(end-start), 0, 1)
    height = (2*t**3-3*t*t+1)*y0+(t**3-2*t*t+t)*(end-start)*slope+(-2*t**3+3*t*t)*level
    p[station >= start, 1] = height[station >= start]
    width = 4.5+3.5*np.clip((station-start)/25, 0, 1)
    vertices, triangles = make_strip(p, 8)
    vertices = np.array(vertices).reshape(-1, 2, 3)
    centers = vertices.mean(axis=1, keepdims=True)
    vertices = centers+(vertices-centers)*(width/8)[:, None, None]
    faces = vertices.reshape(-1, 3)[triangles]
    if np.any(np.cross(faces[:, 1]-faces[:, 0], faces[:, 2]-faces[:, 0])[:, 1] >= -1e-8):
        raise ValueError('Folded apron')
    center = np.array([np.interp(596, station, p[:, j]) for j in range(3)])
    forward = np.array([np.interp(597, station, p[:, j])-np.interp(595, station, p[:, j]) for j in range(3)])
    forward[1] = 0
    forward /= np.linalg.norm(forward)
    return p, station, vertices.reshape(-1, 3), triangles, {
        'status': 'synthetic_technical_stop_not_PV01',
        'center_m': center.tolist(), 'forward': forward.tolist(),
        'width_m': 4.5, 'length_m': 8.0, 'level_m': float(level),
        'design_start_station_m': start, 'flat_from_station_m': end,
        'apron_width_m': 8.0, 'hold_s': 1.5,
        'surveyed_dimensions': False, 'pedestrian_connection_verified': False,
    }


def main():
    folder = ROOT/'build/circuit'
    inputs = {n: (folder/n).read_bytes() for n in ['pilot_manifest.json', 'pilot_road.json']}
    manifest = json.loads(inputs['pilot_manifest.json'])
    road = json.loads(inputs['pilot_road.json'])
    p, station, vertices, triangles, parking = design(road)
    tail = p[station >= 545]
    entries = {tuple(e['offset_xz_m']): e for e in manifest['sectors']}
    cache = {}

    def chunk(key):
        if key not in cache:
            e = entries[key]
            b = (folder/e['path']).read_bytes()
            if hashlib.sha256(b).hexdigest() != e['sha256']:
                raise ValueError('Changed input chunk')
            cache[key] = json.loads(b)
        return cache[key]

    def old_height(x, z):
        key = (math.floor(x/128)*128, math.floor(z/128)*128)
        if key not in entries:
            candidates = [(key[0]-128,key[1]),(key[0],key[1]-128),(key[0]-128,key[1]-128)]
            key = next((k for k in candidates if k in entries and 0 <= x-k[0] <= 128 and 0 <= z-k[1] <= 128), None)
            if key is None:
                raise ValueError('Missing parking halo coverage')
        return chunk(key)['heights_m'][round((z-key[1])/2)*65+round((x-key[0])/2)]

    def graded(x, z):
        dist, level = closest(tail, x, z)
        old = np.array([old_height(a, b) for a, b in zip(x.ravel(), z.ravel())]).reshape(x.shape)
        if not np.isfinite(old).all():
            raise ValueError('No invented terrain fill allowed')
        # Keep the exact existing profile at the beginning; regrade only the new approach.
        forward = tail[1, [0, 2]]-tail[0, [0, 2]]
        ahead = (x-tail[0, 0])*forward[0]+(z-tail[0, 2])*forward[1] >= 0
        _, original_level = closest(np.array(road['points_m']), x, z)
        changed_level = np.abs(level-original_level) > 1e-6
        t = np.clip((dist-5)/8, 0, 1)
        blend = (1-t*t*(3-2*t))*changed_level*ahead
        return old+(level-.35-old)*blend

    build_id = hashlib.sha256(inputs['pilot_road.json']+Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()[:20]
    changed = []
    max_cut = 0.0
    for key, e in entries.items():
        ox, oz = key
        if not (tail[:, 0].min()-16 <= ox+128 and ox <= tail[:, 0].max()+16
                and tail[:, 2].min()-16 <= oz+128 and oz <= tail[:, 2].max()+16):
            continue
        d = json.loads(json.dumps(chunk(key)))
        x, z = np.meshgrid(ox+np.arange(65)*2, oz+np.arange(65)*2)
        old = np.array(d['heights_m']).reshape(65, 65)
        new = graded(x, z)
        max_cut = max(max_cut, float(np.abs(new-old).max()))
        normals = np.array(d['normals']).reshape(65, 65, 3)
        dist, _ = closest(tail, x, z)
        mask = dist < 16
        xx, zz = x[mask], z[mask]
        n = np.column_stack([-(graded(xx+2, zz)-graded(xx-2, zz))/4,
                             np.ones(xx.size), -(graded(xx, zz+2)-graded(xx, zz-2))/4])
        n /= np.linalg.norm(n, axis=1)[:, None]
        normals[mask] = n
        d['heights_m'] = np.round(new, 6).ravel().tolist()
        d['normals'] = np.round(normals, 6).reshape(-1, 3).tolist()
        d['synthetic_parking_grading'] = True
        b = encode(d)
        e['path'] = f'datasets/parking_{build_id}/{d["id"]}.json'
        e['sha256'] = hashlib.sha256(b).hexdigest()
        e['overview']['heights_m'] = np.round(new[::4, ::4], 6).ravel().tolist()
        e['overview']['normals'] = np.round(normals[::4, ::4], 6).reshape(-1, 3).tolist()
        atomic_write(folder/e['path'], b)
        changed.append(key)
    seam = 0.0
    for key in entries:
        for dx, dz in [(128, 0), (0, 128)]:
            other = (key[0]+dx, key[1]+dz)
            if other not in entries or (key not in changed and other not in changed):
                continue
            a = np.array(json.loads((folder/entries[key]['path']).read_bytes())['heights_m']).reshape(65, 65)
            b = np.array(json.loads((folder/entries[other]['path']).read_bytes())['heights_m']).reshape(65, 65)
            seam = max(seam, float(np.abs(a[:, -1]-b[:, 0] if dx else a[-1]-b[0]).max()))
    if seam > 1e-5:
        raise ValueError('Parking terrain seam changed')
    road.update(points_m=p.tolist(), vertices_m=vertices.tolist(), triangles=triangles, parking=parking)
    delta = np.diff(p, axis=0)
    road['length_3d_m'] = float(np.linalg.norm(delta, axis=1).sum())
    road['max_design_grade'] = float(np.max(np.abs(delta[:, 1])/np.linalg.norm(delta[:, [0, 2]], axis=1)))
    road['width_status'] = '4.5m approach flares to 8m technical apron; all design parameters, not surveyed'
    road['scope'] = 'Technical stop only; not PV-01, village visit or approved road geometry'
    manifest['synthetic_parking'] = parking
    atomic_write(folder/'parking_manifest.json', encode(manifest))
    atomic_write(folder/'parking_road.json', encode(road))
    report = {'parking': parking, 'changed_chunks': len(changed), 'max_additional_cut_fill_m': max_cut,
              'max_seam_error_m': seam, 'pilot_inputs_sha256': {n: hashlib.sha256(b).hexdigest() for n, b in inputs.items()},
              'max_profile_change_m': float(np.abs(p[:, 1]-np.array(json.loads(inputs['pilot_road.json'])['points_m'])[:, 1]).max())}
    atomic_write(folder/'parking_generation_report.json', encode(report))
    for n, b in inputs.items():
        assert (folder/n).read_bytes() == b
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
