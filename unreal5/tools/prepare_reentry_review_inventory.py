"""Denser access search with explicit rejection counts; no geometry mutation."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import shapely
from pyproj import Transformer
from road_surface import RoadSurface
from prepare_reentry_checks import NativeGround,OSM

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--itinerary',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--step-m',type=float,default=5)
    parser.add_argument('--diagnostic-station',type=float,action='append',default=[],
                        help='Retain this station despite the conservative grade screen, explicitly flagged for a physical diagnostic')
    args=parser.parse_args()
    if args.output.exists():raise RuntimeError('Preserve the earlier access inventory')
    if not 1<=args.step_m<=30:raise ValueError('Search spacing must stay between 1 and 30 m')
    m=json.loads(args.manifest.read_text());origin=np.asarray(m['origin_ENH_m']);route=json.loads(args.itinerary.read_text())
    if route['build_id']!=m['build_id']:raise RuntimeError('Mismatched input generations')
    forward_projection=Transformer.from_crs(4326,6708,always_xy=True);inverse=Transformer.from_crs(6708,4326,always_xy=True)
    fields=[];properties=[];obstacles=[]
    for feature in json.loads(OSM.read_text())['features']:
        prop=feature['properties'];g=shapely.geometry.shape(feature['geometry'])
        g=shapely.transform(g,forward_projection.transform,interleaved=False)
        g=shapely.transform(g,lambda p:np.column_stack([p[:,0]-origin[0],origin[1]-p[:,1]]))
        if prop.get('landuse')=='meadow' or prop.get('natural')=='grassland':fields.append(g);properties.append(prop)
        if prop.get('building'):obstacles.append(g.buffer(.5))
        if prop.get('barrier'):obstacles.append(g.buffer(1))
        if prop.get('natural')=='water' or prop.get('waterway'):obstacles.append(g.buffer(5))
    field_tree=shapely.STRtree(fields);obstacle_tree=shapely.STRtree(obstacles)
    road=RoadSurface(m,include_shoulders=True);ground=NativeGround(m)
    points=np.asarray(route['points_cm'])[:,:2]/100;station=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    counts={};candidates=[];geometric_rejections=[];diagnostics=[]
    def reject(reason):counts[reason]=counts.get(reason,0)+1
    if any(not math.isfinite(s) or not 30<=s<station[-1]-30 for s in args.diagnostic_station):
        raise ValueError('Diagnostic stations must lie inside the sampled itinerary')
    stations=np.unique(np.r_[np.arange(30,station[-1]-30,args.step_m),args.diagnostic_station])
    for s in stations:
        center=np.array([np.interp(s,station,points[:,j]) for j in range(2)])
        before=np.array([np.interp(s-8,station,points[:,j]) for j in range(2)]);after=np.array([np.interp(s+8,station,points[:,j]) for j in range(2)])
        u=center-before;v=after-center;u/=np.linalg.norm(u);v/=np.linalg.norm(v)
        turn=math.degrees(math.acos(np.clip(u@v,-1,1)))
        if turn>3:reject('road_turn_over_three_degrees');continue
        tangent=u+v;tangent/=np.linalg.norm(tangent)
        for side in [1,-1]:
            normal=side*np.array([-tangent[1],tangent[0]]);lateral=np.array([-normal[1],normal[0]])
            basis=np.vstack([normal,lateral]);field_rect=shapely.Polygon(center+np.array([[6,-1.3],[12,-1.3],[12,1.3],[6,1.3]])@basis)
            ids=field_tree.query(field_rect,predicate='intersects')
            if not len(ids) or not shapely.union_all([fields[i] for i in ids]).covers(field_rect):reject('mapped_grass_cover_incomplete');continue
            sweep=shapely.Polygon(center+np.array([[-2.5,-1.5],[12.5,-1.5],[12.5,1.5],[-2.5,1.5]])@basis)
            if len(obstacle_tree.query(sweep,predicate='intersects')):reject('mapped_obstacle_in_sweep');continue
            along=np.arange(-2.5,12.51,.25);cross=np.array([-1.05,0,1.05]);locations=center+along[:,None,None]*normal+cross[None,:,None]*lateral
            native=ground.sample(locations.reshape(-1,2)).reshape(len(along),len(cross))
            if not np.isfinite(native).all():reject('missing_native_ground');continue
            z,distance=road.sample(locations.reshape(-1,2)*100);z=z.reshape(native.shape)/100;distance=distance.reshape(native.shape)/100
            top=np.where(distance<.0001,np.maximum(native,z),native);grade=float(np.abs(np.diff(top,axis=0)/.25).max())
            passes_grade=grade<=.20
            if not passes_grade:
                reject('sampled_grade_over_original_twenty_percent_limit');geometric_rejections.append({'station_m':float(s),'side':side,'maximum_grade':grade})
                if not any(abs(s-requested)<1e-8 for requested in args.diagnostic_station):continue
            height,d=road.sample(center*100)
            if d[0]>.0001:reject('spawn_outside_road');continue
            lon,lat=inverse.transform(center[0]+origin[0],origin[1]-center[1])
            candidate={'station_m':float(s),'center_UE_cm':[*list(center*100),float(height[0])],
                'forward_UE_xy':normal.tolist(),'yaw_rad':math.atan2(normal[1],normal[0]),'longitude':lon,'latitude':lat,
                'max_sampled_grade':grade,'height_range_m':float(np.ptp(top)),'road_turn_degrees':turn,
                'grass_source_features':[properties[i] for i in ids],'profile_s_m':along.tolist(),'surface_height_m':top[:,1].tolist(),
                'passes_default_geometric_grade_screen':passes_grade,
                'requires_explicit_physical_diagnostic':not passes_grade,
                'status':'Unreviewed geometric candidate. Street View access/obstacle check and physical reentry still required.'}
            (candidates if passes_grade else diagnostics).append(candidate)
    candidates.sort(key=lambda c:(c['max_sampled_grade'],c['height_range_m']))
    report={'build_id':m['build_id'],'manifest_sha256':sha(args.manifest),'itinerary_sha256':sha(args.itinerary),'source_osm_sha256':sha(OSM),
        'input_sha256':{str(p.resolve()):sha(p) for p in [args.manifest,args.itinerary,Path(__file__),ROOT/'tools/prepare_reentry_checks.py',ROOT/'tools/road_surface.py']},
        'search_station_spacing_m':args.step_m,'maximum_candidate_grade':.20,'maximum_road_turn_degrees':3,
        'method':'Original conservative envelope, exclusion and slope rules; denser station sampling. Explicit diagnostic stations retain failed grade screens in a separate list. No terrain, physics or test acceptance thresholds changed.',
        'rejection_counts':counts,'grade_rejections':geometric_rejections,'candidates':candidates,'physically_driven':False,
        'requested_diagnostic_stations_m':args.diagnostic_station,'physical_diagnostic_candidates':diagnostics,
        'coverage_status':'Mapped grass does not prove absence of unrecorded houses, poles, fences or drainage. Visual source validation remains mandatory.'}
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(args.output.resolve()),'candidates':len(candidates),'rejection_counts':counts,
        'summary':[{k:c[k] for k in ['station_m','longitude','latitude','max_sampled_grade']} for c in candidates]},indent=2))


if __name__=='__main__':main()
