"""Choose a low-grade mapped road location for a bare-ground driving diagnostic."""
import json
import math
from pathlib import Path
import numpy as np
from pyproj import Transformer
import shapely
from shapely.geometry import shape,box,Point

root=Path(__file__).resolve().parents[1]
m=json.loads((root/'terrain/valle_first/manifest.json').read_text())
raw=np.fromfile(root/'terrain/valle_first/Valle_505.r16',dtype='<u2').reshape(505,505)
heights=(raw.astype(float)-32768)/128*m['landscape']['z_scale']+m['landscape']['actor_z_cm']
mask=np.fromfile(root/'terrain/valle_first/vegetation_mask.bin',dtype='u1').reshape(505,505)
e0,n0,h0=m['origin_ENH_m'];project=Transformer.from_crs(4326,6708,always_xy=True)
inside=box(20,20,232,232)
def local(g):
    g=shapely.transform(g,project.transform,interleaved=False)
    return shapely.transform(g,lambda coords:np.column_stack([coords[:,0]-e0,n0-coords[:,1]]))
def elevation(x,y):
    fx,fy=x*2,y*2;ix,iy=int(fx),int(fy);ax,ay=fx-ix,fy-iy
    return float((1-ay)*((1-ax)*heights[iy,ix]+ax*heights[iy,ix+1])+ay*((1-ax)*heights[iy+1,ix]+ax*heights[iy+1,ix+1]))
features=json.loads((Path(__file__).resolve().parents[1] / 'data/geography/osm_survey.geojson').read_text(encoding='utf-8'))['features']
buildings=shapely.union_all([local(shape(f['geometry'])) for f in features if f['properties'].get('building')])
candidates=[]
for feature in features:
    tags=feature['properties']
    if tags.get('highway') not in ('residential','unclassified','service','tertiary'):continue
    line=local(shape(feature['geometry']))
    if line.geom_type!='LineString':continue
    for distance in np.arange(8,max(8,line.length-8),2):
        p=line.interpolate(distance)
        if not inside.contains(p) or buildings.distance(p)<7:continue
        before,after=line.interpolate(distance-5),line.interpolate(distance+5)
        dx,dy=after.x-before.x,after.y-before.y
        if math.hypot(dx,dy)<8:continue
        gx=(elevation(p.x+0.5,p.y)-elevation(p.x-0.5,p.y))/100
        gy=(elevation(p.x,p.y+0.5)-elevation(p.x,p.y-0.5))/100
        slope=math.degrees(math.atan(math.hypot(gx,gy)))
        candidates.append((slope+0.01*p.distance(Point(126,126)),p,math.degrees(math.atan2(dy,dx)),slope,tags))
if not candidates:raise RuntimeError('No suitable mapped road candidate in this crop')
_,p,yaw,slope,tags=min(candidates,key=lambda c:c[0])
report={'position_cm':[p.x*100,p.y*100,elevation(p.x,p.y)+60], 'yaw_deg':yaw,
        'local_ground_slope_deg':slope,'mapped_highway':tags,'origin_ENH_m':m['origin_ENH_m'],
        'status':'diagnostic spawn on bare LiDAR terrain near mapped road centerline',
        'road_surface_verified':False,'road_width_observed':False}
(root/'parameters/terrain_spawn.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
