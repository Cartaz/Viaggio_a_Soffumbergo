"""A feasible driving line at the reviewed west junction of the Canal bridge.

Only navigation is rounded. Source roads, asphalt, shoulders and LiDAR remain
unchanged. The conservative car envelope must fit the existing built surface
and avoid mapped buildings before the line is accepted for a physical trial.
"""
import math
import numpy as np
import shapely
from pyproj import Transformer
import json
from pathlib import Path


def round_canal_junction(points, labels, surface, origin, bridge):
    en=np.asarray(bridge['coordinates_EN_m'])[[0,-1]]
    ends=np.column_stack([en[:,0]-origin[0],origin[1]-en[:,1]])*100
    corner=ends[np.argmin(ends[:,0])]
    matches=[]
    for i in np.flatnonzero(np.linalg.norm(points-corner,axis=1)<.1):
        if i==0 or i>=len(points)-1:continue
        a=points[i]-points[i-1];b=points[i+1]-points[i]
        turn=math.atan2(a[0]*b[1]-a[1]*b[0],a@b)
        if math.radians(100)<abs(turn)<math.radians(170):matches.append((i,turn))
    if len(matches)!=1:raise RuntimeError('Reviewed Canal junction no longer matches the route')
    index,turn=matches[0];c=points[index]
    u=c-points[index-1];u/=np.linalg.norm(u)
    v=points[index+1]-c;v/=np.linalg.norm(v)
    radius=517.;distance=radius*math.tan(abs(turn)/2)
    station=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    start=station[index]-distance;end=station[index]+distance
    before=np.searchsorted(station,start,side='left');after=np.searchsorted(station,end,side='right')
    # Tangencies must lie on the two straight arms, not cross another junction.
    for q in points[before:index+1]:
        if abs((q-c)[0]*u[1]-(q-c)[1]*u[0])>.1:raise RuntimeError('Incoming arm is not straight')
    for q in points[index:after]:
        if abs((q-c)[0]*v[1]-(q-c)[1]*v[0])>.1:raise RuntimeError('Outgoing arm is not straight')
    a=c-u*distance;center=a+np.array([-u[1],u[0]])*radius*np.sign(turn)
    first=math.atan2(a[1]-center[1],a[0]-center[0])
    angle=first+np.linspace(0,turn,math.ceil(radius*abs(turn)/25)+1)
    arc=center+radius*np.column_stack([np.cos(angle),np.sin(angle)])
    yaw=angle+np.sign(turn)*math.pi/2
    allowed=surface.local_drivable_polygon(c,25).buffer(2)
    root=Path(__file__).resolve().parents[1]
    source=(Path(__file__).resolve().parents[1] / 'data/geography/osm_circuit_environment.geojson')
    projection=Transformer.from_crs(4326,6708,always_xy=True)
    buildings=[]
    for f in json.loads(source.read_text())['features']:
        if not f['properties'].get('building'):continue
        geom=shapely.transform(shapely.geometry.shape(f['geometry']),projection.transform,interleaved=False)
        geom=shapely.transform(geom,lambda p:np.column_stack([p[:,0]-origin[0],origin[1]-p[:,1]])*100)
        if geom.intersects(allowed):buildings.append(geom.buffer(25))
    blocked=shapely.union_all(buildings)
    for xy,h in zip(arc,yaw):
        co,si=math.cos(h),math.sin(h)
        body=xy+128*np.array([co,si])
        rect=np.array([[-215,-105],[215,-105],[215,105],[-215,105]])@np.array([[co,si],[-si,co]])+body
        footprint=shapely.Polygon(rect)
        if not allowed.covers(footprint):raise RuntimeError('Rounded driving line leaves the built surface')
        if footprint.intersects(blocked):raise RuntimeError('Rounded driving line overlaps a mapped building')
    records={'id':'CANAL-WEST-JUNCTION','bridge_id':bridge['id'],
             'corner_UE_cm':c.tolist(),'turn_degrees':math.degrees(turn),
             'rear_path_radius_m':radius/100,'wheelbase_m':2.56,'rear_axle_offset_m':1.28,
             'body_envelope_m':[4.3,2.1],'sample_spacing_max_cm':25,
             'body_samples_checked':len(arc),'building_clearance_m':.25,
             'surface_numeric_tolerance_cm':2,'geometry_clear':True,'physically_driven':False,
             'world_geometry_modified':False,'source_roads_modified':False,
             'status':'Engineering driving line within existing asphalt and shoulders; not a measured road radius'}
    new_points=np.vstack([points[:before],arc,points[after:]])
    new_labels=labels[:before]+[labels[index]]*len(arc)+labels[after:]
    assert len(new_labels)==len(new_points)-1
    return new_points,new_labels,records
