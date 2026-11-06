"""Check actual shoulder triangles for unsupported strips beside bridge decks."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import shapely

p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path)
args=p.parse_args();root=Path(__file__).resolve().parents[1]
source=args.manifest or Path(json.loads((root/'parameters/current_road_design.json').read_text())['manifest'])
m=json.loads(source.read_text());origin=np.asarray(m['origin_ENH_m'])
triangles=[];precision=[]
for mesh in m['meshes']:
    if mesh['kind']!='shoulder':continue
    data=json.loads(Path(mesh['source']).read_text())
    v=(np.asarray(data['vertices_cm'])+np.asarray(mesh['location_cm']))/100
    triangles.append(v[np.asarray(data['triangles']),:2])
    precision.append(mesh.get('boundary_quantization',{}))
polys=shapely.polygons(np.concatenate(triangles));tree=shapely.STRtree(polys)
checks=[]
for b in json.loads((root/'results/territory/bridge_review.json').read_text())['bridges']:
    if b['crossing_role']!='traversed_span':continue
    en=np.asarray(b['coordinates_EN_m'])[[0,-1]]
    xy=np.column_stack([en[:,0]-origin[0],origin[1]-en[:,1]])
    direction=xy[1]-xy[0];direction/=np.linalg.norm(direction)
    line=shapely.LineString([xy[0]+direction*.001,xy[1]-direction*.001])
    width=m['config']['major_road_width_m'] if b['properties'].get('highway')=='secondary' else m['config']['width_m']
    zone=line.buffer(width/2+m['config']['shoulder_m']-.001,cap_style='flat').difference(
        shapely.LineString(xy).buffer(width/2+.001,cap_style='flat'))
    ids=tree.query(zone,predicate='intersects')
    area=float(shapely.area(shapely.intersection(polys[ids],zone)).sum())
    checks.append({'bridge':b['id'],'unsupported_shoulder_area_m2':area,'clear':area<1e-6})
baseline=json.loads((root/'terrain/road_design/1a13bc28041e/manifest.json').read_text())
def mesh_hashes(data):return {a['id']:a['sha256'] for a in data['meshes'] if a['kind']=='asphalt'}
def terrain_hashes(data):
    return {t['id']:(hashlib.sha256(Path(t['heightmap']).read_bytes()).hexdigest(),
                     hashlib.sha256(Path(t['holes']).read_bytes()).hexdigest()) for t in data['tiles']}
report={'build_id':m['build_id'],'baseline_build_id':baseline['build_id'],
        'scope':'Actual generated triangle footprints beside the three spans; unchanged asphalt and terrain checked against the physically driven baseline. Not an engine or full-lap test.',
        'bridges':checks,'asphalt_unchanged':mesh_hashes(m)==mesh_hashes(baseline),
        'terrain_heights_and_masks_unchanged':terrain_hashes(m)==terrain_hashes(baseline),
        'collapsed_shoulder_boundary_faces_removed':sum(x.get('collapsed_boundary_faces_removed',0) for x in precision),
        'boundary_area_removed_m2':sum(x.get('original_boundary_area_removed_m2',0) for x in precision)}
report['passed']=all(c['clear'] for c in checks) and report['asphalt_unchanged'] and report['terrain_heights_and_masks_unchanged']
(root/('results/bridge_shoulders_'+m['build_id']+'.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
if not report['passed']:raise SystemExit(1)
