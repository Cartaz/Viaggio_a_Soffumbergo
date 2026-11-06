"""Independent geometric audit of planned bodies against built surfaces and OSM footprints."""
import json
import math
from pathlib import Path
import numpy as np
import shapely
from pyproj import Transformer
from road_surface import RoadSurface

root=Path(__file__).resolve().parents[1]
data=json.loads((root/'Unreal/Content/Data/circuit_itinerary.json').read_text())
m=json.loads(Path(json.loads((root/'parameters/current_road_design.json').read_text())['manifest']).read_text())
origin=np.asarray(json.loads((root/'terrain/world_tiles/manifest.json').read_text())['origin_ENH_m'])
source=(Path(__file__).resolve().parents[1] / 'data/geography/osm_circuit_environment.geojson')
projection=Transformer.from_crs(4326,6708,always_xy=True)
buildings=[]
for f in json.loads(source.read_text())['features']:
    if not f['properties'].get('building') or f['geometry']['type'] not in ['Polygon','MultiPolygon']:continue
    g=shapely.transform(shapely.geometry.shape(f['geometry']),projection.transform,interleaved=False)
    g=shapely.transform(g,lambda p:np.column_stack([(p[:,0]-origin[0])*100,(origin[1]-p[:,1])*100]))
    buildings.append((str(f.get('id')),g))
tree=shapely.STRtree([g for _,g in buildings]);surface=RoadSurface(m);results=[]
for turn,stop in zip(data['maneuvers'],data['stops']):
    allowed=surface.local_drivable_polygon(stop['position_cm'][:2],21).buffer(2)
    overlaps=[];outside=[]
    for i,p in enumerate(turn['poses']):
        yaw=p['yaw_rad'];c,s=math.cos(yaw),math.sin(yaw)
        rect=np.array([[-215,-105],[215,-105],[215,105],[-215,105]])
        rect=rect@np.array([[c,s],[-s,c]])+np.asarray(p['root_cm'])
        footprint=shapely.Polygon(rect)
        missing=footprint.difference(allowed).area/10000
        if missing>.001:outside.append({'pose':i,'outside_area_m2':missing})
        for j in tree.query(footprint,predicate='intersects'):
            area=footprint.intersection(buildings[j][1]).area/10000
            if area>.001:overlaps.append({'pose':i,'building':buildings[j][0],'overlap_m2':area})
    results.append({'name':turn['name'],'poses':len(turn['poses']),'surface_envelope_violations':outside,
                    'mapped_building_overlaps':overlaps,'clear':not outside and not overlaps})
report={'build_id':m['build_id'],'building_source':str(source),'building_footprints_checked':len(buildings),
        'body_envelope_m':[4.3,2.1],'surface_numeric_tolerance_cm':2,'turns':results,
        'all_clear':all(r['clear'] for r in results),'physical_execution_verified':False}
(root/'results/maneuver_clearance_audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
