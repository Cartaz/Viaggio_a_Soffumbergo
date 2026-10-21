"""Generate local shoulder meshes; leave original DTM, road and grading untouched."""
import hashlib
import json
from pathlib import Path
import numpy as np
import shapely
from shapely import Polygon, box
from build_circuit_3d import encode, atomic_write
from coffa.road_construction import road_footprint, triangulate_surface
from coffa.road_shoulders import EdgeIndex, ramp_height, terrain_height, conforming_triangles

ROOT = Path(__file__).resolve().parents[1]


def main():
    folder = ROOT/'build/circuit'
    source = folder/'construction_manifest.json'
    doc = json.loads(source.read_bytes())
    construction = doc['engineering_construction']
    config_path = ROOT/'data/config/circuit_shoulders.json'
    config = json.loads(config_path.read_bytes())
    if not 0 < config['width_m'] <= config['vehicle_nominal_width_m']/2:
        raise ValueError('Shoulder must be no wider than half the vehicle')
    fingerprint = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                   for p in [config_path, Path(__file__), ROOT/'tools/coffa/road_shoulders.py', ROOT/'tools/coffa/road_construction.py']}
    fingerprint['construction_manifest'] = hashlib.sha256(source.read_bytes()).hexdigest()
    build_id = hashlib.sha256(encode(fingerprint)).hexdigest()[:20]
    profile = np.array(construction['profile_points_m'])
    c = construction['report']['config']
    station = np.r_[0, np.cumsum(np.linalg.norm(np.diff(profile[:, [0, 2]], axis=0), axis=1))]
    t = np.diff(profile[:, [0, 2]], axis=0)/np.diff(station)[:, None]
    angles = np.degrees(np.arccos(np.clip((t*np.roll(t, 1, axis=0)).sum(axis=1), -1, 1)))
    aprons = np.where((angles >= c['corner_apron_min_degrees']) & (angles <= c['corner_apron_max_degrees']))[0]
    footprint = road_footprint(profile, c['width_m'], aprons, c['corner_apron_radius_m']).simplify(c['footprint_simplify_m'], preserve_topology=True)
    edges, chunks = [], {}
    for entry in doc['sectors']:
        raw = (folder/entry['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('Changed ground chunk')
        chunks[tuple(entry['offset_xz_m'])] = json.loads(raw)
    for entry in construction['road_sectors']:
        raw = (folder/entry['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('Changed road chunk')
        data = json.loads(raw)
        v, faces = np.asarray(data['vertices_m']), np.asarray(data['triangles'])
        e = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
        unique, count = np.unique(e, axis=0, return_counts=True)
        boundary = v[unique[count == 1]]
        mid = boundary[:, :, [0, 2]].mean(axis=1)
        boundary = boundary[shapely.distance(shapely.points(mid), footprint.boundary) < max(2e-5, c.get('road_geometry_precision_m', 0)*2)]
        edges.extend(boundary)
    edge_index = EdgeIndex(edges)
    atomic_write(ROOT/'build/shoulder_validation/boundary.json', encode(edge_index.edges.tolist()))
    lines = shapely.line_merge(shapely.MultiLineString(edge_index.edges[:, :, [0, 2]].tolist()))
    rings = list(shapely.get_parts(lines))
    if not all(shapely.is_closed(r) for r in rings):
        raise ValueError('Road mesh boundary is not closed')
    rings.sort(key=lambda r: Polygon(r).area, reverse=True)
    actual = Polygon(rings[0].coords, [r.coords for r in rings[1:]])
    if not actual.is_valid or abs(actual.area-footprint.area) > .5:
        raise ValueError('Road boundary reconstruction mismatch')
    corridor = actual.buffer(config['width_m'], quad_segs=8).difference(actual)

    class Sampler:
        def query(self, x, z, _radius):
            d, road = edge_index.sample(x, z)
            ground = terrain_height(chunks, x, z)
            height = ramp_height(d, road, ground, config['width_m'], config['ground_cover_m'])
            return d, height, np.zeros(len(d), dtype=int)

    entries = []
    for e in doc['sectors']:
        ox, oz = e['offset_xz_m']
        part = corridor.intersection(box(ox, oz, ox+128, oz+128))
        if part.is_empty or part.area < 1e-8:
            continue
        xz, f = conforming_triangles(part, (ox, oz), config['geometry_precision_m'])
        _, height, _ = Sampler().query(xz[:, 0], xz[:, 1], 1)
        if not np.isfinite(height).all():
            raise ValueError('Shoulder exceeds available terrain')
        v = np.column_stack([xz[:, 0], np.round(height, 6), xz[:, 1]])
        raw = encode({'id':e['id'], 'vertices_m':v.tolist(), 'triangles':f.tolist(),
                      'status':'continuous_design_shoulder_not_surveyed'})
        path = f'datasets/shoulders_{build_id}/{e["id"]}.json'
        atomic_write(folder/path, raw)
        entries.append({'id':e['id'], 'path':path, 'sha256':hashlib.sha256(raw).hexdigest(),
                        'vertices':len(v), 'triangles':len(f)})
        if len(entries) % 25 == 0:
            print('Shoulder sectors:', len(entries), flush=True)
    manifest = {'schema_version':1, 'build_id':build_id, 'config':config,
                'construction_manifest_sha256':fingerprint['construction_manifest'], 'fingerprints':fingerprint,
                'sectors':entries, 'triangles':sum(e['triangles'] for e in entries),
                'original_rasters_modified':False, 'road_mesh_modified':False}
    atomic_write(folder/'shoulders.json', encode(manifest))
    print(json.dumps({k:v for k, v in manifest.items() if k not in ['sectors', 'fingerprints']}, indent=2))


if __name__ == '__main__':
    main()
