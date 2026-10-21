"""Independent local-float32 mesh fronts, tile seams and Jolt reference rays."""
import hashlib
import json
from pathlib import Path
import numpy as np
import shapely
from shapely import STRtree
from build_circuit_3d import encode, atomic_write
from coffa.road_shoulders import terrain_height
from coffa.loop_route import stationing, cut

ROOT = Path(__file__).resolve().parents[1]


def mesh_height(faces, tree, q):
    qi, fi = tree.query(shapely.points(q), predicate='intersects')
    unique, first = np.unique(qi, return_index=True)
    result = np.full(len(q), np.nan)
    f, pos = faces[fi[first]], q[unique]
    a, b = f[:, 1, [0, 2]]-f[:, 0, [0, 2]], f[:, 2, [0, 2]]-f[:, 0, [0, 2]]
    r = pos-f[:, 0, [0, 2]]
    det = a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0]
    u = (r[:, 0]*b[:, 1]-r[:, 1]*b[:, 0])/det
    v = (a[:, 0]*r[:, 1]-a[:, 1]*r[:, 0])/det
    result[unique] = f[:, 0, 1]+u*(f[:, 1, 1]-f[:, 0, 1])+v*(f[:, 2, 1]-f[:, 0, 1])
    return result


def main():
    folder = ROOT/'build/circuit'
    doc = json.loads((folder/'shoulders.json').read_bytes())
    construction_path = folder/'construction_manifest.json'
    assert doc['construction_manifest_sha256'] == hashlib.sha256(construction_path.read_bytes()).hexdigest()
    construction = json.loads(construction_path.read_bytes())
    chunks = {tuple(e['offset_xz_m']):json.loads((folder/e['path']).read_bytes()) for e in construction['sectors']}
    edges = np.array(json.loads((ROOT/'build/shoulder_validation/boundary.json').read_bytes()))
    # Probe uniformly around the entire asphalt boundary, not only one easy straight.
    edges = edges[::max(1, len(edges)//1200)]
    center = edges.mean(axis=1)[:, [0, 2]]
    tangent = edges[:, 1, [0, 2]]-edges[:, 0, [0, 2]]
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    normal /= np.linalg.norm(normal, axis=1)[:, None]
    query = np.concatenate([center+sign*normal*offset for offset in [.01, .1, .5, 1, 2, 4.9] for sign in [-1, 1]])
    keys = np.floor(query/128).astype(int)*128
    entries = {tuple(map(int, e['id'].split('_'))):e for e in doc['sectors']}
    meshes, groups, seams = {}, [], 0
    minimum_cover = float('inf')
    for key, entry in entries.items():
        raw = (folder/entry['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry['sha256']
        data = json.loads(raw)
        v, indices = np.array(data['vertices_m']), np.array(data['triangles'])
        faces = v[indices]
        cross = np.cross(faces[:, 1]-faces[:, 0], faces[:, 2]-faces[:, 0])[:, 1]
        assert (cross < 0).all(), 'Degenerate shoulder face '+entry['id']
        local = (v-[key[0], 0, key[1]]).astype(np.float32)[indices]
        assert (np.cross(local[:, 1]-local[:, 0], local[:, 2]-local[:, 0])[:, 1] < 0).all(), 'Local float32 shoulder face lost '+entry['id']
        sample = np.vstack([v, faces.mean(axis=1)])
        ground = terrain_height(chunks, sample[:, 0], sample[:, 2])
        minimum_cover = min(minimum_cover, float((sample[:, 1]-ground).min()))
        tree = STRtree(shapely.polygons(faces[:, :, [0, 2]]))
        ids = np.where((keys == key).all(axis=1))[0]
        height = mesh_height(faces, tree, query[ids])
        valid = np.isfinite(height)
        if valid.any():
            groups.append({'id':entry['id'], 'points_m':np.column_stack([query[ids[valid], 0], height[valid], query[ids[valid], 1]]).tolist()})
        meshes[key] = v
    for key, a in meshes.items():
        x, z = key
        for dx, dz in [(128, 0), (0, 128)]:
            b = meshes.get((x+dx, z+dz))
            if b is None:
                continue
            axis, value = (0, x+128) if dx else (2, z+128)
            aa = sorted(tuple(p) for p in a[np.abs(a[:, axis]-value) < 1e-7])
            bb = sorted(tuple(p) for p in b[np.abs(b[:, axis]-value) < 1e-7])
            assert aa == bb, 'Shoulder tile seam '+str(key)
            seams += 1
    assert minimum_cover > -.002, 'Ground intrudes through shoulder mesh: '+str(minimum_cover)
    result = {'passed':True, 'sectors':len(entries), 'triangles':doc['triangles'],
              'local_float32_fronts_verified':True, 'tile_seams':seams,
              'minimum_vertex_and_centroid_ground_cover_m':minimum_cover,
              'reference_rays':sum(len(g['points_m']) for g in groups)}
    atomic_write(ROOT/'build/shoulder_validation/probes.json', encode(groups))
    atomic_write(ROOT/'build/shoulder_validation/geometry_report.json', encode(result))
    p = np.array(construction['engineering_construction']['profile_points_m'])
    station = stationing(p)
    for start in np.arange(1000., station[-1]-220, 50):
        route = cut(p, station, start, start+200)
        tangent = np.diff(route[:, [0, 2]], axis=0)
        lengths = np.linalg.norm(tangent, axis=1)
        tangent /= lengths[:, None]
        if (tangent@tangent[0]).min() < .995 or (np.abs(np.diff(route[:, 1])/lengths)).max() > .06:
            continue
        normal = np.array([-tangent[0, 1], tangent[0, 0]])
        lateral = np.concatenate([route[:, [0, 2]]+normal*sign*5 for sign in [-1, 1]])
        ground = terrain_height(chunks, lateral[:, 0], lateral[:, 1])
        if np.isfinite(ground).all() and np.max(np.abs(ground-np.tile(route[:, 1], 2))) < 1:
            atomic_write(ROOT/'build/shoulder_validation/recovery_route.json', encode(
                {'id':'Uscita e rientro', 'points_m':route.tolist(), 'source_station_range_m':[start, start+200]}))
            result['recovery_source_station_range_m'] = [start, start+200]
            break
    else:
        raise ValueError('No gentle documented test stretch found')
    atomic_write(ROOT/'build/shoulder_validation/geometry_report.json', encode(result))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
