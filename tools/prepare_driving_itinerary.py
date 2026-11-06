"""Resolve the documented panorama detour, preserving every real stop branch."""
import hashlib
import argparse
import json
import math
from pathlib import Path
import numpy as np
from pyproj import Transformer
from road_surface import RoadSurface
from navigation_line import round_canal_junction
from navigation_alignment import on_derived_axis

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path)
p.add_argument('--reuse-maneuvers',type=Path,help='Reuse only when all three stop positions and headings are identical')
args=p.parse_args()
pointer=json.loads((root/'parameters/current_road_design.json').read_text())
m=json.loads((args.manifest or Path(pointer['manifest'])).read_text())
output=args.output or root/'Unreal/Content/Data/circuit_itinerary.json'
if args.output and output.exists():raise RuntimeError('Preserve prior draft itinerary; choose a fresh output')
route_path=(Path(__file__).resolve().parents[1] / 'data/geography/circuito_osm_candidate_20261020.geojson')
route=json.loads(route_path.read_text());original=route['features'][0]['geometry']['coordinates']
assert original[3]==original[7] and original[4]==original[6]
assert original[5]==[13.345662,46.1524543]
# The westbound spur existed only to snap to panorama CIR-02. The documented
# instruction is a left turn at the junction, without the extra reversal.
route['features'][0]['geometry']['coordinates']=original[:4]+original[8:]
origin=np.asarray(json.loads((root/'terrain/world_tiles/manifest.json').read_text())['origin_ENH_m'])
transform=Transformer.from_crs(4326,6708,always_xy=True)
points=[];labels=[]
for f in route['features']:
    en=np.asarray([transform.transform(*p[:2]) for p in f['geometry']['coordinates']])
    xy=np.column_stack([en[:,0]-origin[0],origin[1]-en[:,1]])*100
    for a,b in zip(xy,xy[1:]):
        count=max(1,math.ceil(np.linalg.norm(b-a)/200))
        points.extend(a+(b-a)*i/count for i in range(count));labels.extend([f['properties']['sector']]*count)
points=np.vstack([points,points[0]])
points,alignment_transfer=on_derived_axis(points,m)
surface=RoadSurface(m,include_shoulders=True)
bridge=next(b for b in json.loads((root/'results/territory/bridge_review.json').read_text())['bridges'] if b['id']=='way/207100551')
points,labels,driving_line=round_canal_junction(points,labels,surface,origin,bridge)
z,d=surface.sample(points)
assert d.max()<.2,'Navigation leaves the generated asphalt'
xyz=np.column_stack([points,z]);lengths=np.linalg.norm(np.diff(points,axis=0),axis=1)
station=np.r_[0,np.cumsum(lengths)]/100
tangent=np.diff(points,axis=0)/lengths[:,None]
angle=np.arccos(np.clip((tangent*np.roll(tangent,1,axis=0)).sum(1),-1,1))
reversal=np.flatnonzero(angle>math.radians(179.9))
assert len(reversal)==3
records=[]
for i,name in zip(reversal,['Campeglio','Valle','Canal di Grivò']):
    records.append({'name':name,'index':int(i),'station_m':float(station[i]),'position_cm':xyz[i].tolist(),
                    'arrival_yaw_rad':float(math.atan2(tangent[i-1,1],tangent[i-1,0])),
                    'departure_yaw_rad':float(math.atan2(tangent[i,1],tangent[i,0])),
                    'physical_maneuver_verified':False})
data={'build_id':m['build_id'],'points_cm':xyz.tolist(),'station_m':station.tolist(),'sectors':labels,'stops':records,
      'alignment_transfer':alignment_transfer,
      'driving_line_corrections':[driving_line],
      'route_length_m':float(station[-1]),'full_lap_verified':False,
      'correction':{'id':'REV-FAEDIS','removed_only_panorama_anchor_backtrack':True,'other_stop_branches_preserved':True,
                    'junction_wgs84':original[3],'anchor_wgs84':original[5],
                    'evidence':'Original sector A instructions: two left turns, no reversal. Street View at the junction shows the continuous turn into the main street.',
                    'source_survey':'data/geography/sector_a_survey.json',
                    'streetview_url':'https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=46.1524147,13.3458246&heading=25',
                    'displayed_location':'11 SP15, Faedis','displayed_image_date':'2024-08',
                    'observation':'Paved T junction with a small traffic island, stop markings on the northern arm, main street continuous across the junction. No turnaround is needed to join the southeast-bound street.',
                    'original_geometry_sha256':hashlib.sha256(route_path.read_bytes()).hexdigest(),
                    'source_geometry_modified':False,'parking_access_metric_verified':False}}
if args.reuse_maneuvers:
    previous=json.loads(args.reuse_maneuvers.read_text())
    for current,old_stop in zip(records,previous['stops'],strict=True):
        if current['name']!=old_stop['name'] or np.max(np.abs(np.asarray(current['position_cm'][:2])-old_stop['position_cm'][:2]))>.001:
            raise RuntimeError('Stop position changed: regenerate maneuver plans')
        if any(abs(current[k]-old_stop[k])>1.e-8 for k in ['arrival_yaw_rad','departure_yaw_rad']):
            raise RuntimeError('Stop heading changed: regenerate maneuver plans')
    data['maneuvers']=previous['maneuvers']
    for turn,stop in zip(data['maneuvers'],records,strict=True):turn['index']=stop['index']
    data['maneuver_plan_reuse']={'source_build_id':previous['build_id'],'three_stop_planar_poses_identical':True,
                                 'road_height_delta_at_stops_cm':[current['position_cm'][2]-old_stop['position_cm'][2] for current,old_stop in zip(records,previous['stops'],strict=True)],
                                 'new_world_physical_driving_verified':False}
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(data))
review=output.parent/(output.stem+'_review.json') if args.output else root/'results/driving_itinerary_review.json'
review.write_text(json.dumps({k:data[k] for k in ['build_id','route_length_m','stops','correction','alignment_transfer','full_lap_verified']},indent=2))
line_review=output.parent/'navigation_line_review.json' if args.output else root/'results/navigation_line_review.json'
line_review.write_text(json.dumps(driving_line,indent=2))
print(json.dumps({'route_length_m':data['route_length_m'],'real_stop_branches':len(records),'navigation_points':len(points)}))
