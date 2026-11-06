"""Measure the actual serialized road triangles, independently of design axes."""
import argparse
import json
from pathlib import Path
import numpy as np
from road_surface import RoadSurface

p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
args=p.parse_args()
if args.output.exists():raise RuntimeError('Preserve previous audit')
m=json.loads(args.manifest.read_text());surface=RoadSurface(m)
t=surface.faces/100;ab=t[:,1]-t[:,0];ac=t[:,2]-t[:,0]
den=ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
gx=(ab[:,2]*ac[:,1]-ac[:,2]*ab[:,1])/den
gy=(ab[:,0]*ac[:,2]-ac[:,0]*ab[:,2])/den
grade=np.hypot(gx,gy)
area=np.abs(den)/2;edges=np.linalg.norm(np.roll(t[:,:,:2],-1,axis=1)-t[:,:,:2],axis=2)
altitude=np.abs(den)/edges.max(axis=1)
representative=(area>=.01)&(altitude>=.01)
limit=m['config']['pavement_maximum_grade'];tolerance=.002
report={'build_id':m['build_id'],'passed':bool(np.isfinite(grade).all() and grade[representative].max()<=limit+tolerance),
        'pavement_faces':len(t),'representative_faces':int(representative.sum()),
        'maximum_representative_grade':float(grade[representative].max()),'maximum_all_serialized_grade':float(grade.max()),
        'grade_limit':limit,'serialized_coordinate_tolerance':tolerance,
        'representative_face_filter':'area >= 0.01 m2 and shortest altitude >= 1 cm; same numeric scale as interior native probes',
        'world_modified':False,'physically_driven':False,
        'scope':'Serialized geometry after coordinate rounding. Does not replace native collision or a driven lap.'}
args.output.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if not report['passed']:raise SystemExit(1)
