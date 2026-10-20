"""Check a locally generated scene against sources and adjacent sector edges."""
import argparse
import json
import math
from pathlib import Path

from build_valle_3d import ROOT, sha


def check(path):
    doc = json.loads(path.read_text(encoding='utf-8'))
    assert doc['cell_centres_used'] and not doc['datum_conversion_applied']
    assert doc['osm_sha256'] == sha(ROOT/'data/geography/osm_survey.geojson')
    assert doc['config_sha256'] == sha(ROOT/'data/config/valle_3d.json')
    sectors = {tuple(s['offset_xz_m']): s for s in doc['sectors']}
    seams = 0
    for (x, z), sector in sectors.items():
        n = sector['side']
        assert len(sector['heights_m']) == n*n == len(sector['normals'])
        assert all(math.isfinite(h) for h in sector['heights_m'])
        assert sector['skirt_depth_m'] > max(sector['lod_max_error_m'])
        for dx, dz in [(128, 0), (0, 128)]:
            neighbor = sectors.get((x+dx, z+dz))
            if neighbor is None:
                continue
            for i in range(n):
                a, b = (i*n+n-1, i*n) if dx else ((n-1)*n+i, i)
                assert sector['heights_m'][a] == neighbor['heights_m'][b]
                assert sector['normals'][a] == neighbor['normals'][b]
            seams += 1
    osm = json.loads((ROOT/'data/geography/osm_survey.geojson').read_text(encoding='utf-8'))
    ids = {f['id'] for f in osm['features'] if 'building' in f['properties']}
    assert {b['id'] for b in doc['buildings']} == ids
    for b in doc['buildings']:
        assert b['height_status'] == doc['config']['building_height_status']
        assert b['roof_y_m'] > b['base_y_m']
    assert all('no_road_collision' in road['status'] for road in doc['roads'])
    assert next(a for a in doc['anchors'] if a['id'] == 'PV-01')['status'] == 'observed_not_user_confirmed'
    result = {'scene_sha256': sha(path), 'seams_checked': seams,
              'max_shared_edge_error_m': 0, 'building_count': len(ids),
              'sector_count': len(sectors), 'source_config_checks_passed': True}
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    args = parser.parse_args()
    check(args.scene)
