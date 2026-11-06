"""Read-only OSM coverage/exclusions extract for the entire native terrain envelope."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request
import numpy as np
from pyproj import Transformer
import shapely
from shapely.ops import polygonize

ROOT = Path(__file__).resolve().parents[1]


def convert(data):
    features = []; consumed = set(); incomplete = []
    for e in data['elements']:
        if e['type'] != 'relation': continue
        tags = e.get('tags', {})
        if tags.get('type') not in ['multipolygon', 'boundary']: continue
        rings = {'outer': [], 'inner': []}; ids = []
        for member in e.get('members', []):
            role = member.get('role') or 'outer'
            if role not in rings or member.get('type') != 'way': continue
            q = [[p['lon'], p['lat']] for p in member.get('geometry', []) if p]
            if len(q) >= 2:
                rings[role].append(shapely.LineString(q)); ids.append(member['ref'])
        outer = list(polygonize(shapely.union_all(rings['outer'])))
        if not outer:
            incomplete.append(e['id']); continue
        geometry = shapely.union_all(outer)
        inner = list(polygonize(shapely.union_all(rings['inner'])))
        if inner: geometry = geometry.difference(shapely.union_all(inner))
        if not geometry.is_valid: geometry = shapely.make_valid(geometry)
        features.append({'type': 'Feature', 'id': 'relation/'+str(e['id']), 'properties': tags,
                         'geometry': shapely.geometry.mapping(geometry)})
        consumed.update(ids)
    for e in data['elements']:
        if e['type'] != 'way' or e['id'] in consumed: continue
        q = [[p['lon'], p['lat']] for p in e.get('geometry', []) if p]
        if len(q) < 2: continue
        tags = e.get('tags', {})
        area = q[0] == q[-1] and len(q) >= 4 and tags.get('area') != 'no' and not tags.get('highway') and not tags.get('waterway') and not tags.get('power')
        g = shapely.Polygon(q) if area else shapely.LineString(q)
        if not g.is_valid: g = shapely.make_valid(g)
        features.append({'type': 'Feature', 'id': 'way/'+str(e['id']), 'properties': tags,
                         'geometry': shapely.geometry.mapping(g)})
    return {'type': 'FeatureCollection', 'features': features}, incomplete


def main():
    p = argparse.ArgumentParser(); p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--endpoint', default='https://overpass-api.de/api/interpreter')
    p.add_argument('--group', choices=['all', 'cover', 'access', 'water', 'buildings', 'roads'], default='all')
    args = p.parse_args()
    if args.output.exists(): raise RuntimeError('Preserve previous extract')
    m = json.loads(args.manifest.read_text()); o = m['origin_ENH_m']
    b = np.array([t['bounds_xy_cm'] for t in m['tiles']])/100
    inverse = Transformer.from_crs(6708, 4326, always_xy=True)
    corners = [inverse.transform(o[0]+x, o[1]-y) for x in [b[:, 0].min(), b[:, 2].max()] for y in [b[:, 1].min(), b[:, 3].max()]]
    lon, lat = np.array(corners).T
    bbox = [lat.min()-.0003, lon.min()-.0003, lat.max()+.0003, lon.max()+.0003]
    bounds = ','.join(f'{v:.9f}' for v in bbox)
    groups = {'cover': ['landuse', 'natural~"^(wood|scrub|grassland)$"'],
              'access': ['building', 'highway'], 'water': ['waterway', 'natural=water', 'power~"^(line|minor_line)$"']}
    groups['buildings'] = ['building']; groups['roads'] = ['highway']
    selectors = sorted(set(sum(groups.values(), []))) if args.group == 'all' else groups[args.group]
    query = '[out:json][timeout:40];(\n'+''.join(f'{kind}[{s}]({bounds});\n' for s in selectors for kind in ['way', 'relation'])+');out body geom;'
    args.output.mkdir(parents=True)
    (args.output/'query.txt').write_text(query)
    url = args.endpoint
    request = urllib.request.Request(url+'?'+urllib.parse.urlencode({'data': query}), headers={'User-Agent': 'SoffumbergoLocalTerrainResearch/1.0'})
    try:
        with urllib.request.urlopen(request, timeout=50) as response: raw = response.read()
        (args.output/'response.json').write_bytes(raw); data = json.loads(raw)
        if data.get('remark'): raise RuntimeError('Overpass returned incomplete response: '+data['remark'])
        collection, incomplete = convert(data)
        if incomplete: raise RuntimeError('Unassembled area relations: '+str(incomplete))
        (args.output/'cover.geojson').write_text(json.dumps(collection, separators=(',', ':')))
        report = {'source_url': url, 'query': query, 'group': args.group, 'bbox_south_west_north_east': bbox,
                  'retrieved_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'osm_base_timestamp': data.get('osm3s', {}).get('timestamp_osm_base'),
                  'response_sha256': hashlib.sha256(raw).hexdigest(),
                  'geojson_sha256': hashlib.sha256((args.output/'cover.geojson').read_bytes()).hexdigest(),
                  'elements': len(data['elements']), 'features': len(collection['features']), 'incomplete_relations': incomplete,
                  'license': 'ODbL-1.0', 'attribution': 'OpenStreetMap contributors', 'license_url': 'https://www.openstreetmap.org/copyright',
                  'limitations': ['Mapped plan geometry, not surveyed species or individual plant positions.', 'Coverage and setbacks need scene/source review; missing map features are not evidence of absence.']}
        (args.output/'provenance.json').write_text(json.dumps(report, indent=2)); print(json.dumps(report, indent=2))
    except BaseException as error:
        (args.output/'failure.json').write_text(json.dumps({'error': repr(error)}, indent=2)); raise


if __name__ == '__main__': main()
