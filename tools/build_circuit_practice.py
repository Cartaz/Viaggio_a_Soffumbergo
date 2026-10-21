"""Partition the unchanged engineering axis into explicit practice sections.

No manoeuvre is simulated by a route shortcut. Selecting a section is a declared
training relocation, never completion of the journey or a driven full lap.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from build_circuit_3d import encode, atomic_write

ROOT = Path(__file__).resolve().parents[1]


def sections(route, profile, trim_regular=6., trim_reversal=18.):
    p = np.asarray(profile, dtype=float)
    lengths = np.linalg.norm(np.diff(p[:, [0, 2]], axis=0), axis=1)
    if np.any(lengths <= 0) or not np.isfinite(p).all():
        raise ValueError('Invalid practice profile')
    station = np.r_[0., np.cumsum(lengths)]
    tangent = np.diff(p[:, [0, 2]], axis=0)/lengths[:, None]
    angle = np.degrees(np.arccos(np.clip((tangent*np.roll(tangent, 1, axis=0)).sum(axis=1), -1, 1)))
    reversals = set(np.where(angle > 179.99)[0].tolist())
    boundaries = {0, len(p)-1} | reversals
    count = 0
    sector_ranges = []
    for f in route:
        start = count
        count += len(f['points_m'])-1
        boundaries.add(count)
        sector_ranges.append((f['sector'], start, count))
    if count != len(p)-1:
        raise ValueError('Route/profile station counts differ')
    result = []
    def is_reversal(index):
        return index % (len(p)-1) in reversals
    for a, b in zip(sorted(boundaries), sorted(boundaries)[1:]):
        start = station[a]+(trim_reversal if is_reversal(a) else trim_regular)
        end = station[b]-(trim_reversal if is_reversal(b) else trim_regular)
        if end-start < 20:
            raise ValueError('Practice segment too short; review trimming explicitly')
        def at(s):
            i = min(len(p)-2, max(0, np.searchsorted(station, s, side='right')-1))
            return p[i]+(p[i+1]-p[i])*(s-station[i])/lengths[i]
        mid = p[(station > start) & (station < end)]
        points = np.vstack([at(start), mid, at(end)])
        sector = next(name for name, lo, hi in sector_ranges if lo <= a < hi)
        number = 1+sum(s['sector'] == sector for s in result)
        result.append({'id':f'{sector}{number}', 'sector':sector, 'points_m':points.tolist(),
                       'source_station_range_m':[float(station[a]), float(station[b])],
                       'usable_station_range_m':[float(start), float(end)],
                       'length_horizontal_m':float(end-start),
                       'start_trim_m':float(start-station[a]), 'end_trim_m':float(station[b]-end),
                       'stop_reason':'unresolved_maneuver' if is_reversal(b) else 'practice_sector_boundary',
                       'starts_after_unresolved_maneuver':is_reversal(a)})
    return result, sorted(reversals)


def main():
    folder = ROOT/'build/circuit'
    path = folder/'construction_manifest.json'
    manifest = json.loads(path.read_bytes())
    review_path = ROOT/'data/geography/circuit_maneuver_review.json'
    review = json.loads(review_path.read_bytes())
    for item in review['items']:
        if not (ROOT/item['source']).is_file():
            raise ValueError('Missing documentary source: '+item['source'])
    stage, reversals = sections(manifest['route'], manifest['engineering_construction']['profile_points_m'])
    if len(reversals) != len(review['items']):
        raise ValueError('Maneuver review no longer matches the axis')
    from pyproj import Transformer, network
    network.set_network_enabled(False)
    projection = Transformer.from_crs(6708, 4326, always_xy=True, allow_ballpark=False)
    origin = manifest['origin_ENH_m']
    for i, index in enumerate(reversals):
        point = manifest['engineering_construction']['profile_points_m'][index]
        # Explicit positions link the review to the unchanged source, not just an issue count.
        lon, lat = projection.transform(point[0]+origin[0], origin[1]-point[2])
        if np.linalg.norm(np.array([lon, lat])-review['items'][i]['wgs84']) > 1e-7:
            raise ValueError('Maneuver order/location changed')
    total = sum(s['length_horizontal_m'] for s in stage)
    result = {'schema_version':1, 'status':'training_sections_not_complete_journey',
              'construction_manifest_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
              'maneuver_review_sha256':hashlib.sha256(review_path.read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
              'sections':stage, 'maneuver_review':review, 'section_count':len(stage),
              'usable_length_m':total, 'excluded_end_buffers_m':manifest['engineering_construction']['report']['route_length_horizontal_m']-total,
              'full_lap_driven':False, 'real_maneuvers_verified':False}
    atomic_write(folder/'practice.json', encode(result))
    print(json.dumps({k:v for k, v in result.items() if k not in ['sections', 'maneuver_review']}, indent=2))


if __name__ == '__main__':
    main()
