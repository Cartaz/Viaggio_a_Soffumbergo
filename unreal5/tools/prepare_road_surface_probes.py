"""Prepare independent width, triangle and bridge-underdeck collision probes."""
import argparse
import json
from pathlib import Path
import numpy as np
from road_surface import RoadSurface

p=argparse.ArgumentParser();p.add_argument('--publish',action='store_true')
p.add_argument('--manifest',type=Path);p.add_argument('--runtime',type=Path)
args=p.parse_args()
root=Path(__file__).resolve().parents[1]
source=args.manifest or Path(json.loads((root/'parameters/current_road_design.json').read_text())['manifest'])
m=json.loads(source.read_text());surface=RoadSurface(m)
profile=np.asarray(m['profile_UE_cm']);points=[]
for offset in [-200,-115,0,115,200]:
    tangent=np.diff(profile[:,:2],axis=0);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
    q=profile[:-1,:2]+np.column_stack([-tangent[:,1],tangent[:,0]])*offset
    z,distance=surface.sample(q)
    if distance.max()>.2:raise RuntimeError('Width probe outside generated asphalt')
    points.extend(np.column_stack([q,z]).tolist())
width_count=len(points)
tri=surface.faces
edges=np.roll(tri[:,:,:2],-1,axis=1)-tri[:,:,:2]
area2=np.abs(edges[:,0,0]*(-edges[:,2,1])-edges[:,0,1]*(-edges[:,2,0]))
altitude=area2/np.linalg.norm(edges,axis=2).max(axis=1)
ids=np.flatnonzero((area2>=200)&(altitude>=1))[::8]
points.extend(tri[ids].mean(axis=1).tolist())
origin=np.asarray(m['origin_ENH_m']);void=[]
for b in json.loads((root/'results/territory/bridge_review.json').read_text())['bridges']:
    if b['crossing_role']!='traversed_span':continue
    en=np.asarray(b['coordinates_EN_m'])[[0,-1]]
    xy=np.column_stack([en[:,0]-origin[0],origin[1]-en[:,1]])*100
    q=xy[0]+np.array([.25,.5,.75])[:,None]*(xy[1]-xy[0])
    z,_=surface.sample(q)
    void.extend(np.column_stack([q,z-45]).tolist())
result={'build_id':m['build_id'],'road_survey_points_cm':points,'road_void_probes_cm':void,
        'coverage':{'axis_samples':len(profile)-1,'width_offsets_cm':[-200,-115,0,115,200],
                    'width_probes':width_count,'triangle_centroid_probes':len(ids),
                    'triangle_filter':'every eighth face with area >= 0.01 m2 and altitude >= 1 cm; excludes numerically tiny boundary faces',
                    'underdeck_probes':len(void),'underdeck_interval_below_asphalt_cm':[45,65]},
        'scope':'Collision probes across carriageway width, selected face interiors and air below three bridge decks; not a driven lap'}
target=source.parent/'expanded_surface_probes.json';target.write_text(json.dumps(result))
if args.publish:
    path=args.runtime or root/'Unreal/Content/Data/circuit_driving_world.json';data=json.loads(path.read_text())
    assert data['build_id']==m['build_id']
    for key in ['road_survey_points_cm','road_void_probes_cm']:data[key]=result[key]
    data['road_probe_coverage']=result['coverage']
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(data));temporary.replace(path)
coverage=root/('results/road_probe_coverage_'+m['build_id']+'.json' if args.manifest else 'results/road_probe_coverage.json')
coverage.write_text(json.dumps({k:v for k,v in result.items() if not k.endswith('_cm')},indent=2))
print(json.dumps(result['coverage']))
