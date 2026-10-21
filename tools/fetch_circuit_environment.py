"""Cache a separate OSM environment extract; never downloads Google imagery."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = 'https://overpass-api.de/api/interpreter'
QUERY = '''[out:json][timeout:60];(
 way[building](46.125,13.342,46.172,13.398);
 way[natural](46.125,13.342,46.172,13.398);
 way[landuse](46.125,13.342,46.172,13.398);
 way[barrier](46.125,13.342,46.172,13.398);
 node[natural=tree](46.125,13.342,46.172,13.398);
 node[highway=street_lamp](46.125,13.342,46.172,13.398);
 node[power=pole](46.125,13.342,46.172,13.398);
);out tags geom;'''


def normalize(raw):
    if raw.get('remark') or not isinstance(raw.get('elements'), list):
        raise ValueError('Incomplete or failed Overpass response')
    features = []
    for e in raw['elements']:
        if e['type'] == 'node':
            geometry = {'type': 'Point', 'coordinates': [e['lon'], e['lat']]}
        else:
            coords = [[p['lon'], p['lat']] for p in e.get('geometry', [])]
            if len(coords) < 2:
                continue
            closed = len(coords) > 3 and coords[0] == coords[-1]
            geometry = {'type': 'Polygon' if closed else 'LineString',
                        'coordinates': [coords] if closed else coords}
        features.append({'type': 'Feature', 'id': f"{e['type']}/{e['id']}",
                         'geometry': geometry, 'properties': e.get('tags', {})})
    if not features:
        raise ValueError('Empty environment response')
    return {'type': 'FeatureCollection', 'coordinate_reference': 'EPSG:4326 lon lat',
            'attribution': '© OpenStreetMap contributors, ODbL 1.0',
            'features': sorted(features, key=lambda f: f['id'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--download', action='store_true')
    mode.add_argument('--input', type=Path)
    args = parser.parse_args()
    if args.download:
        req = urllib.request.Request(ENDPOINT, data=urllib.parse.urlencode({'data': QUERY}).encode(),
                                     headers={'User-Agent': 'Viaggio-a-Soffumbergo-environment/0.1'})
        with urllib.request.urlopen(req, timeout=70) as stream:
            payload = stream.read(25_000_001)
    else:
        payload = args.input.read_bytes()
    if len(payload) > 25_000_000:
        raise ValueError('Oversize response')
    data = normalize(json.loads(payload))
    cache = ROOT/'build/streetview'
    cache.mkdir(parents=True, exist_ok=True)
    (cache/'environment.raw.json').write_bytes(payload)
    out = ROOT/'data/geography'
    (out/'osm_circuit_environment.geojson').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    meta = {'source_url': ENDPOINT, 'query': QUERY,
            'downloaded_utc': datetime.now(timezone.utc).isoformat() if args.download else None,
            'source_response_sha256': hashlib.sha256(payload).hexdigest(),
            'osm_base_timestamp': json.loads(payload).get('osm3s', {}).get('timestamp_osm_base'),
            'feature_count': len(data['features']), 'license': 'ODbL-1.0',
            'limitations': ['OSM plan geometry only; not a survey', 'No imagery, facades or measured heights',
                            'Regional extract; runtime uses only the terrain corridor']}
    (out/'osm_circuit_environment_provenance.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(meta))


if __name__ == '__main__':
    main()
