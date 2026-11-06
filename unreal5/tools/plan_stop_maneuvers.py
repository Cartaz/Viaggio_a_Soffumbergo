"""Plan real forward/reverse steering paths inside built asphalt and shoulders.

Hybrid A* uses the Yaris wheelbase and steering limit. It never adds a turning
pad, moves the vehicle, or counts a geometric path as a driven maneuver.
"""
import heapq
import itertools
import json
import math
from pathlib import Path
import time
import numpy as np
import shapely
from pyproj import Transformer
from road_surface import RoadSurface

ROOT=Path(__file__).resolve().parents[1]
GRID=.2;BINS=72;REAR=1.28;WB=2.56;STEER=.46;STEP=.6
def angle(x):return (x+math.pi)%(2*math.pi)-math.pi

def plan(stop,surface,building_tree,building_polygons):
    started=time.monotonic();center=np.asarray(stop['position_cm'])[:2]
    poly=surface.local_drivable_polygon(center,21)
    hits=building_tree.query(poly,predicate='intersects')
    blocked=shapely.union_all([building_polygons[i] for i in hits]) if len(hits) else shapely.GeometryCollection()
    poly=shapely.transform(poly,lambda p:(p-center)/100).buffer(.02)
    if not blocked.is_empty:poly=poly.difference(shapely.transform(blocked,lambda p:(p-center)/100).buffer(.25))
    shapely.prepare(poly)
    axis=np.arange(-16,16+.01,GRID);n=len(axis);xx,yy=np.meshgrid(axis,axis)
    bad=(~shapely.contains_xy(poly,xx,yy)).astype(float)
    half=18;ka=np.arange(-half,half+1)*GRID;kx,ky=np.meshgrid(ka,ka)
    size=1<<(n+2*half-1).bit_length();fb=np.fft.rfft2(bad,s=(size,size))
    safe=[]
    for h in range(BINS):
        yaw=h*2*math.pi/BINS;c,s=math.cos(yaw),math.sin(yaw)
        longitudinal=kx*c+ky*s;lateral=-kx*s+ky*c
        # Physical chassis is 3.8 x 1.68 m; use a larger body envelope here.
        kernel=((longitudinal>=REAR-2.15)&(longitudinal<=REAR+2.15)&(np.abs(lateral)<=1.05)).astype(float)
        collision=np.fft.irfft2(fb*np.fft.rfft2(kernel[::-1,::-1],s=(size,size)),s=(size,size))
        safe.append(collision[half:half+n,half:half+n]<.5)
    safe=np.asarray(safe)
    def valid(x,y,yaw):
        col=round((x+16)/GRID);row=round((y+16)/GRID);h=round((yaw%(2*math.pi))*BINS/(2*math.pi))%BINS
        if not(half<=col<n-half and half<=row<n-half and safe[h,row,col]):return False
        c,s=math.cos(yaw),math.sin(yaw)
        body=np.array([x+REAR*c,y+REAR*s])
        rect=np.array([[-2.15,-1.05],[2.15,-1.05],[2.15,1.05],[-2.15,1.05]])@np.array([[c,s],[-s,c]])+body
        return bool(shapely.covers(poly,shapely.Polygon(rect)))
    yaw=stop['arrival_yaw_rad'];goal_yaw=stop['departure_yaw_rad']
    start=(-REAR*math.cos(yaw),-REAR*math.sin(yaw),yaw)
    goal=np.array([-REAR*math.cos(goal_yaw),-REAR*math.sin(goal_yaw)])
    if not valid(*start):raise RuntimeError('Starting envelope does not fit '+stop['name'])
    def key(x,y,yaw,d):return (round(x/GRID),round(y/GRID),round(yaw*BINS/(2*math.pi))%BINS,d)
    def heuristic(x,y,yaw):return max(math.hypot(x-goal[0],y-goal[1]),WB/math.tan(STEER)*abs(angle(yaw-goal_yaw)))
    # x, y, yaw, g, parent, incoming direction, incoming steering
    nodes=[(*start,0.,-1,0,0.)];heap=[(heuristic(*start),0)];cost={key(*start,0):0.};winner=None
    while heap and len(nodes)<350000:
        _,index=heapq.heappop(heap);x,y,yaw,g,parent,previous_direction,previous_steer=nodes[index]
        if g>cost.get(key(x,y,yaw,previous_direction),math.inf)+1.e-8:continue
        if math.hypot(x-goal[0],y-goal[1])<.3 and abs(angle(yaw-goal_yaw))<math.radians(5):winner=index;break
        for direction,steer in itertools.product([1,-1],[0,STEER,-STEER]):
            nx,ny,na=x,y,yaw;ok=True
            for _ in range(4):
                ds=direction*STEP/4;curvature=math.tan(steer)/WB
                if abs(curvature)>1.e-8:
                    new_yaw=na+ds*curvature;nx+=(math.sin(new_yaw)-math.sin(na))/curvature;ny+=(-math.cos(new_yaw)+math.cos(na))/curvature;na=new_yaw
                else:nx+=ds*math.cos(na);ny+=ds*math.sin(na)
                if not valid(nx,ny,na):ok=False;break
            if not ok:continue
            na=angle(na);ng=g+STEP*(1 if direction>0 else 1.1)+(2 if previous_direction and direction!=previous_direction else 0)+.15*abs(steer-previous_steer)
            k=key(nx,ny,na,direction)
            if ng>=cost.get(k,math.inf):continue
            cost[k]=ng;nodes.append((nx,ny,na,ng,index,direction,steer));ni=len(nodes)-1
            heapq.heappush(heap,(ng+1.15*heuristic(nx,ny,na),ni))
        if len(nodes)%20000<6:print('TURN_SEARCH '+stop['name']+' '+str(len(nodes)),flush=True)
    if winner is None:raise RuntimeError('No feasible steering path found '+stop['name']+' states='+str(len(nodes)))
    chain=[]
    while winner>=0:chain.append(nodes[winner]);winner=nodes[winner][4]
    chain=chain[::-1]
    poses=[]
    for i,p in enumerate(chain):
        direction=chain[i+1][5] if i==0 else p[5]
        steer=chain[i+1][6] if i==0 else p[6]
        rear=center+np.array(p[:2])*100;body=rear+REAR*100*np.array([math.cos(p[2]),math.sin(p[2])])
        poses.append({'rear_cm':rear.tolist(),'root_cm':body.tolist(),'yaw_rad':p[2],'direction':direction,'steering_rad':steer})
    result={'name':stop['name'],'index':stop['index'],'poses':poses,'search_states':len(nodes),'planning_seconds':time.monotonic()-started,
            'direction_changes':sum(a['direction']!=b['direction'] for a,b in zip(poses,poses[1:])),
            'kinematic_path_found':True,'physically_driven':False,
            'model':{'wheelbase_m':WB,'max_steering_rad':STEER,'rear_axle_offset_m':REAR,'body_length_m':4.3,'body_width_m':2.1,'grid_m':GRID,'heading_bins':BINS},
            'allowed_surface':'existing generated asphalt and shoulders; continuous body-envelope checks, mapped building exclusion with 0.25 m design buffer',
            'surface_numeric_tolerance_cm':2}
    print(json.dumps({k:v for k,v in result.items() if k not in ['poses','model']}),flush=True)
    return result

def main():
    data_path=ROOT/'Unreal/Content/Data/circuit_itinerary.json';itinerary=json.loads(data_path.read_text())
    pointer=json.loads((ROOT/'parameters/current_road_design.json').read_text());manifest=json.loads(Path(pointer['manifest']).read_text())
    assert itinerary['build_id']==manifest['build_id']
    surface=RoadSurface(manifest);turns=[]
    origin=np.asarray(json.loads((ROOT/'terrain/world_tiles/manifest.json').read_text())['origin_ENH_m'])
    projection=Transformer.from_crs(4326,6708,always_xy=True);buildings=[]
    source=Path('C:/Giochi/Sviluppo/Viaggio a Soffumbergo/data/geography/osm_circuit_environment.geojson')
    for f in json.loads(source.read_text())['features']:
        if not f['properties'].get('building') or f['geometry']['type'] not in ['Polygon','MultiPolygon']:continue
        g=shapely.transform(shapely.geometry.shape(f['geometry']),projection.transform,interleaved=False)
        buildings.append(shapely.transform(g,lambda p:np.column_stack([(p[:,0]-origin[0])*100,(origin[1]-p[:,1])*100])))
    tree=shapely.STRtree(buildings)
    for stop in itinerary['stops']:turns.append(plan(stop,surface,tree,buildings))
    itinerary['maneuvers']=turns
    temporary=data_path.with_suffix('.tmp');temporary.write_text(json.dumps(itinerary));temporary.replace(data_path)
    (ROOT/'results/maneuver_planning.json').write_text(json.dumps({'build_id':manifest['build_id'],'turns':turns,'full_lap_driven':False},indent=2))

if __name__=='__main__':main()
