"""Independent geometry/earthworks checks and mesh-height references for Jolt rays."""
import hashlib
import json
from pathlib import Path
import numpy as np
import shapely
from shapely import STRtree
from build_circuit_3d import encode, atomic_write

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT/'build/circuit'
    doc = json.loads((folder/'construction_manifest.json').read_bytes())
    original = json.loads((folder/'manifest.json').read_bytes())
    assert hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest() == doc['engineering_construction']['report']['source_manifest_sha256']
    entries = {tuple(e['offset_xz_m']):e for e in doc['sectors']}
    chunks = {}
    for key, entry in entries.items():
        data = (folder/entry['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
        chunks[key] = json.loads(data)
    edges = 0
    for (x, z), chunk in chunks.items():
        for dx, dz in [(128, 0), (0, 128)]:
            other = chunks.get((x+dx, z+dz))
            if other is None:
                continue
            a = np.asarray(chunk['heights_m'], float).reshape(65, 65)
            b = np.asarray(other['heights_m'], float).reshape(65, 65)
            na = np.asarray(chunk['normals']).reshape(65, 65, 3)
            nb = np.asarray(other['normals']).reshape(65, 65, 3)
            aa, bb = (a[:, -1], b[:, 0]) if dx else (a[-1], b[0])
            an, bn = (na[:, -1], nb[:, 0]) if dx else (na[-1], nb[0])
            np.testing.assert_equal(aa, bb, err_msg='Terrain height seam '+chunk['id'])
            np.testing.assert_allclose(an, bn, atol=1e-6, rtol=0, err_msg='Terrain normal seam '+chunk['id'])
            edges += 1
    road_entries = doc['engineering_construction']['road_sectors']
    roads, meshes = {}, {}
    area, triangles, max_mesh_edge = 0., 0, 0.
    for entry in road_entries:
        data = (folder/entry['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == entry['sha256']
        road = json.loads(data)
        v = np.asarray(road['vertices_m'])
        faces = v[np.asarray(road['triangles'])]
        cross = np.cross(faces[:, 1]-faces[:, 0], faces[:, 2]-faces[:, 0])[:, 1]
        assert (cross < 0).all(), 'Folded/degenerate road face'
        area += float(-cross.sum()/2)
        triangles += len(faces)
        max_mesh_edge = max(max_mesh_edge, float(np.linalg.norm(faces[:, :, [0, 2]]-np.roll(faces[:, :, [0, 2]], 1, axis=1), axis=2).max()))
        roads[entry['id']] = road
        meshes[entry['id']] = (faces, STRtree(shapely.polygons(faces[:, :, [0, 2]])))
    stats = doc['engineering_construction']['report']
    assert abs(area-stats['design_area_m2']) < .01, 'Missing/overlapping design area'
    assert max_mesh_edge <= stats['config']['mesh_max_edge_m']+1e-5
    # Exact matching vertices on each road tile boundary; no cracks/T-junctions.
    road_seams = 0
    for (x, z), entry in entries.items():
        if entry['id'] not in roads:
            continue
        a = np.asarray(roads[entry['id']]['vertices_m'])
        for dx, dz in [(128, 0), (0, 128)]:
            neighbor = entries.get((x+dx, z+dz))
            if neighbor is None or neighbor['id'] not in roads:
                continue
            b = np.asarray(roads[neighbor['id']]['vertices_m'])
            axis, value = (0, x+128) if dx else (2, z+128)
            aa = sorted(tuple(p) for p in a[np.abs(a[:, axis]-value) < 1e-7])
            bb = sorted(tuple(p) for p in b[np.abs(b[:, axis]-value) < 1e-7])
            assert aa == bb, 'Road seam '+entry['id']+' / '+neighbor['id']
            road_seams += 1
    profile = np.asarray(doc['engineering_construction']['profile_points_m'])[:-1]
    tangent = np.roll(profile[:, [0, 2]], -1, axis=0)-np.roll(profile[:, [0, 2]], 1, axis=0)
    zero = np.linalg.norm(tangent, axis=1) < 1e-5
    tangent[zero] = np.roll(profile[:, [0, 2]], -1, axis=0)[zero]-profile[zero][:, [0, 2]]
    tangent /= np.linalg.norm(tangent, axis=1)[:, None]
    normal = np.column_stack([-tangent[:, 1], tangent[:, 0]])
    query = np.concatenate([profile[:, [0, 2]]+normal*offset for offset in [0, -stats['config']['width_m']*.4, stats['config']['width_m']*.4]])
    keys = np.floor(query/128).astype(int)*128
    probes = []
    min_clearance = float('inf')
    for key in np.unique(keys, axis=0):
        ids = np.where((keys == key).all(axis=1))[0]
        entry = entries[tuple(key)]
        faces, tree = meshes[entry['id']]
        qi, fi = tree.query(shapely.points(query[ids]), predicate='intersects')
        unique, first = np.unique(qi, return_index=True)
        assert len(unique) == len(ids), 'Uncovered route/width sample'
        f = faces[fi[first]]
        q = query[ids[unique]]
        a, b = f[:, 1, [0, 2]]-f[:, 0, [0, 2]], f[:, 2, [0, 2]]-f[:, 0, [0, 2]]
        r = q-f[:, 0, [0, 2]]
        det = a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0]
        u = (r[:, 0]*b[:, 1]-r[:, 1]*b[:, 0])/det
        v = (a[:, 0]*r[:, 1]-a[:, 1]*r[:, 0])/det
        height = f[:, 0, 1]+u*(f[:, 1, 1]-f[:, 0, 1])+v*(f[:, 2, 1]-f[:, 0, 1])
        h = np.asarray(chunks[tuple(key)]['heights_m']).reshape(65, 65)
        local = (q-key)/2
        cell = np.floor(local).astype(int)
        uv = local-cell
        c, r = cell[:, 0], cell[:, 1]
        lo = h[r, c]+uv[:, 0]*(h[r, c+1]-h[r, c])+uv[:, 1]*(h[r+1, c]-h[r, c])
        hi = h[r+1, c+1]+(1-uv[:, 0])*(h[r+1, c]-h[r+1, c+1])+(1-uv[:, 1])*(h[r, c+1]-h[r+1, c+1])
        ground = np.where(uv.sum(axis=1) <= 1, lo, hi)
        min_clearance = min(min_clearance, float((height-ground).min()))
        probes.append({'id':entry['id'], 'points_m':np.column_stack([q[:, 0], height, q[:, 1]]).tolist()})
    assert min_clearance > .05, 'Terrain protrudes into design road'
    result = {'passed':True, 'terrain_seams':edges, 'terrain_height_and_normal_seam_error':0,
              'road_seams':road_seams, 'road_triangles':triangles, 'road_plan_area_m2':area,
              'max_horizontal_mesh_edge_m':max_mesh_edge, 'road_reference_rays':len(query),
              'min_sampled_road_terrain_clearance_m':min_clearance,
              'profile_points':len(profile), 'all_route_and_cross_section_samples_covered':True,
              'original_sectors':len(original['sectors'])}
    atomic_write(ROOT/'build/construction_validation/probes.json', encode(probes))
    atomic_write(ROOT/'build/construction_validation/geometry_report.json', encode(result))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
