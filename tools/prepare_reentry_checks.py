"""Choose an observed grass area for a force-driven off-road/reentry trial.

Writes diagnostic inputs only, never production world data or source references.
The initial pose is selected before pawn spawn; subsequent movement is ordinary
throttle/brake/steering. A candidate is not an executed physical test.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import shapely
from pyproj import Transformer
from road_surface import RoadSurface

ROOT = Path(__file__).resolve().parents[1]
OSM = (Path(__file__).resolve().parents[1] / 'data/geography/osm_circuit_environment.geojson')


class NativeGround:
    """Interpolate visible native Landscape triangles from the imported R16."""
    def __init__(self, manifest):
        base = json.loads((ROOT/'terrain/world_tiles/manifest.json').read_text())
        self.quant = base['height_quantization_m']
        self.zero = base['source_height_bounds_m'][0] - manifest['origin_ENH_m'][2]
        self.tiles = manifest['tiles']
        self.arrays = {}

    def sample(self, xy_m):
        p = np.atleast_2d(xy_m)
        out = np.full(len(p), np.nan)
        for tile in self.tiles:
            x0,y0,x1,y1 = np.asarray(tile['bounds_xy_cm'])/100
            ids = np.flatnonzero((p[:,0]>=x0)&(p[:,0]<x1)&(p[:,1]>=y0)&(p[:,1]<y1))
            if not len(ids): continue
            if tile['id'] not in self.arrays:
                n=tile['samples']
                self.arrays[tile['id']] = (np.fromfile(tile['heightmap'],'<u2').reshape(n,n),
                                           np.fromfile(tile['holes'],'u1').reshape(n,n))
            height,holes=self.arrays[tile['id']]
            q=(p[ids]-[x0,y0])/(tile['xy_scale_cm']/100)
            ix,iy=np.floor(q).astype(int).T
            fx,fy=(q-np.floor(q)).T
            # Native Landscape triangulates each cell over top-left/bottom-right.
            a=height[iy,ix].astype(float); b=height[iy,ix+1].astype(float)
            c=height[iy+1,ix].astype(float); d=height[iy+1,ix+1].astype(float)
            z=np.where(fx>=fy, a+(b-a)*fx+(d-b)*fy, a+(d-c)*fx+(c-a)*fy)
            # Reject any cell touching missing data, a conservative source check.
            valid=(holes[iy,ix]==0)&(holes[iy,ix+1]==0)&(holes[iy+1,ix]==0)&(holes[iy+1,ix+1]==0)
            out[ids[valid]]=z[valid]*self.quant+self.zero
        return out


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='results/reentry_candidates_4a05593a4282.json')
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--itinerary',type=Path)
    args=parser.parse_args()
    output=ROOT/args.output
    if output.exists(): raise RuntimeError('Preserve previous candidate set; select a fresh output')
    pointer=json.loads((ROOT/'parameters/current_road_design.json').read_text())
    manifest_path=(args.manifest or Path(pointer['manifest'])).resolve()
    itinerary_path=(args.itinerary or ROOT/'Unreal/Content/Data/circuit_itinerary.json').resolve()
    manifest=json.loads(manifest_path.read_text())
    origin=np.asarray(manifest['origin_ENH_m'])
    projection=Transformer.from_crs(4326,6708,always_xy=True)
    inverse=Transformer.from_crs(6708,4326,always_xy=True)
    fields=[];field_ids=[];blocked=[]
    for feature in json.loads(OSM.read_text())['features']:
        properties=feature['properties']
        g=shapely.geometry.shape(feature['geometry'])
        g=shapely.transform(g,projection.transform,interleaved=False)
        g=shapely.transform(g,lambda p:np.column_stack([p[:,0]-origin[0],origin[1]-p[:,1]]))
        if properties.get('landuse')=='meadow' or properties.get('natural')=='grassland':
            fields.append(g);field_ids.append(properties)
        if properties.get('building'): blocked.append(g.buffer(.5))
        if properties.get('barrier'): blocked.append(g.buffer(1))
        if properties.get('natural')=='water' or properties.get('waterway'):blocked.append(g.buffer(5))
    field_tree=shapely.STRtree(fields);block_tree=shapely.STRtree(blocked)
    road=RoadSurface(manifest,include_shoulders=True)
    ground=NativeGround(manifest)
    itinerary=json.loads(itinerary_path.read_text())
    points=np.asarray(itinerary['points_cm'])[:,:2]/100
    station=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    candidates=[]
    for s in np.arange(30,station[-1]-30,30):
        center=np.array([np.interp(s,station,points[:,j]) for j in range(2)])
        before=np.array([np.interp(s-8,station,points[:,j]) for j in range(2)])
        after=np.array([np.interp(s+8,station,points[:,j]) for j in range(2)])
        u=center-before;v=after-center
        u/=np.linalg.norm(u);v/=np.linalg.norm(v)
        turn=math.degrees(math.acos(np.clip(u@v,-1,1)))
        if turn>3: continue
        tangent=u+v;tangent/=np.linalg.norm(tangent)
        for side in [1,-1]:
            forward=side*np.array([-tangent[1],tangent[0]])
            lateral=np.array([-forward[1],forward[0]])
            field_rect=shapely.Polygon(center+np.array([[6,-1.3],[12,-1.3],[12,1.3],[6,1.3]])@np.vstack([forward,lateral]))
            hits=field_tree.query(field_rect,predicate='intersects')
            if not len(hits):continue
            cover=shapely.union_all([fields[i] for i in hits])
            if not cover.covers(field_rect):continue
            sweep=shapely.Polygon(center+np.array([[-2.5,-1.5],[12.5,-1.5],[12.5,1.5],[-2.5,1.5]])@np.vstack([forward,lateral]))
            if len(block_tree.query(sweep,predicate='intersects')):continue
            along=np.arange(-2.5,12.51,.25);cross=np.array([-1.05,0,1.05])
            locations=center+along[:,None,None]*forward+cross[None,:,None]*lateral
            native=ground.sample(locations.reshape(-1,2)).reshape(len(along),len(cross))
            if not np.isfinite(native).all():continue
            road_z,dist=road.sample(locations.reshape(-1,2)*100)
            road_z=road_z.reshape(native.shape)/100;dist=dist.reshape(native.shape)/100
            top=np.where(dist<.0001,np.maximum(native,road_z),native)
            grades=np.diff(top,axis=0)/.25
            max_grade=float(np.max(np.abs(grades)))
            if max_grade>.20:continue
            xy,xy_dist=road.sample(center*100)
            if xy_dist[0]>.0001:continue
            lng,lat=inverse.transform(center[0]+origin[0],origin[1]-center[1])
            candidates.append({'station_m':float(s),'center_UE_cm':[*list(center*100),float(xy[0])],
                'forward_UE_xy':forward.tolist(),'yaw_rad':math.atan2(forward[1],forward[0]),
                'longitude':lng,'latitude':lat,'max_sampled_grade':max_grade,
                'height_range_m':float(np.ptp(top)),'road_turn_degrees':turn,
                'grass_source_features':[field_ids[i] for i in hits],
                'profile_s_m':along.tolist(),'surface_height_m':top[:,1].tolist(),
                'status':'geometric candidate only; no physical reentry demonstrated'})
    # Initial gentle candidates first; nearby duplicate route passages remain recorded.
    candidates.sort(key=lambda c:(c['max_sampled_grade'],c['height_range_m']))
    report={'build_id':manifest['build_id'],'source_osm_sha256':hashlib.sha256(OSM.read_bytes()).hexdigest(),
            'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'itinerary_sha256':hashlib.sha256(itinerary_path.read_bytes()).hexdigest(),
            'method':'mapped meadow/grassland, conservative vehicle swept envelope, buildings/barriers/water exclusion, current native height samples',
            'coverage_status':'OSM grass cover is reference data, not proof of absence of unmapped fences or curbs',
            'physically_driven':False,'candidates':candidates}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2))
    print(json.dumps({'output':str(output),'candidates':len(candidates),'best':candidates[:2]},indent=2))


if __name__=='__main__':main()
