"""Retain actual DTM cross sections at visually confirmed mapped bridges.

An approach-to-approach line is a diagnostic comparison, not a surveyed deck
height or an automatically approved terrain modification.
"""
import hashlib
import json
import math
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1]
folder=root/'terrain/lidar_mosaic'
m=json.loads((folder/'manifest.json').read_text())
h=np.load(folder/'height_m.npy',mmap_mode='r')
e0,n0=m['origin_E_N_m'];step=m['step_m']
bridges=json.loads((root/'results/territory/bridge_review.json').read_text())['bridges']
offsets=[-8,-4,-2,0,2,4,8]

def sample(p):
    x=(p[0]-e0)/step;y=(n0-p[1])/step
    col,row=math.floor(x),math.floor(y);dx,dy=x-col,y-row
    if not 0<=col<h.shape[1]-1 or not 0<=row<h.shape[0]-1:return None
    v=h[row:row+2,col:col+2]
    if not np.isfinite(v).all():return None
    return float((1-dy)*((1-dx)*v[0,0]+dx*v[0,1])+dy*((1-dx)*v[1,0]+dx*v[1,1]))

records=[]
for bridge in bridges:
    a,b=np.asarray(bridge['coordinates_EN_m'])[[0,-1]]
    length=np.linalg.norm(b-a);direction=(b-a)/length;normal=np.array([-direction[1],direction[0]])
    rows=[]
    for distance in np.arange(-15,length+15,1):
        center=a+direction*distance
        values=[sample(center+normal*offset) for offset in offsets]
        rows.append({'station_from_mapped_start_m':float(distance),'EN_m':center.tolist(),'heights_at_offsets_m':values})
    approach=[r for r in rows if -12<=r['station_from_mapped_start_m']<=-3 or length+3<=r['station_from_mapped_start_m']<=length+12]
    fit=np.polyfit([r['station_from_mapped_start_m'] for r in approach],
                   [r['heights_at_offsets_m'][3] for r in approach],1)
    spans=[r for r in rows if 0<=r['station_from_mapped_start_m']<=length]
    differences=[float(np.polyval(fit,r['station_from_mapped_start_m'])-r['heights_at_offsets_m'][3]) for r in spans]
    records.append({'id':bridge['id'],'view_record':bridge.get('view_record'),
                    'mapped_length_m':float(length),'cross_offsets_m':offsets,'samples':rows,
                    'diagnostic_approach_line_slope':float(fit[0]),
                    'max_center_below_diagnostic_line_m':max(0,max(differences)),
                    'max_center_above_diagnostic_line_m':max(0,-min(differences)),
                    'diagnostic_line_is_surveyed_deck':False,
                    'deck_and_underside_geometry_verified':False})
report={'source_heightmap':str(folder/'height_m.npy'),
        'source_manifest_sha256':hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest(),
        'method':'bilinear sampling of original mosaic at 1 m longitudinal stations; no NoData fill',
        'bridges':records}
(root/'results/territory/bridge_cross_sections.json').write_text(json.dumps(report,indent=2))
print(json.dumps([{k:r[k] for k in ['id','mapped_length_m','max_center_below_diagnostic_line_m','max_center_above_diagnostic_line_m']} for r in records]))
