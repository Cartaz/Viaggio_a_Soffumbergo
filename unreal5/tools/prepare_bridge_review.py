"""Separate mapped bridge spans from bare-earth road-profile candidates."""
import json
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import shape
from shapely import transform, unary_union

root=Path(__file__).resolve().parents[1]
previous=Path('C:/Giochi/Sviluppo/Soffumbergo-Unreal-5-8/data/geography')
network_path=previous/'osm_regional_roads_20261020.geojson'
route_path=Path('C:/Giochi/Sviluppo/Viaggio a Soffumbergo/data/geography/circuito_osm_candidate_20261020.geojson')
network=json.loads(network_path.read_text())
route=json.loads(route_path.read_text())
projection=Transformer.from_crs(4326,6708,always_xy=True)
lines=[(f['properties']['sector'],transform(shape(f['geometry']),projection.transform,interleaved=False)) for f in route['features']]
axis=unary_union([p for _,p in lines])
bridges=[]
observed={v.get('observed_osm_way_id'):v for v in json.loads((root/'results/territory/streetview_verified_20261022.json').read_text())['views'] if v.get('bridge_visually_confirmed')}
for f in network['features']:
    if f['properties'].get('bridge') not in ['yes','viaduct']:continue
    geometry=transform(shape(f['geometry']),projection.transform,interleaved=False)
    distance=geometry.distance(axis)
    if distance>6:continue
    sectors=[s for s,p in lines if p.distance(geometry)<6]
    overlap=geometry.intersection(axis.buffer(.15)).length
    ratio=overlap/geometry.length
    role='traversed_span' if ratio>.8 else 'adjacent_junction_bridge' if ratio<.2 else 'partial_overlap_requires_review'
    bridges.append({'id':f.get('id'),'properties':f['properties'],'geometry_wgs84':f['geometry'],
                    'coordinates_EN_m':[list(p) for p in geometry.coords],
                    'distance_to_candidate_m':distance,'length_m':geometry.length,'near_sectors':sectors,
                    'candidate_span_overlap_m':overlap,'candidate_span_overlap_ratio':ratio,'crossing_role':role,
                    'status':'mapped_span_requires_visual_review','deck_height_measured':False,
                    'terrain_policy':'preserve bare DTM beneath bridge; do not grade a solid embankment across span'})
    observation=observed.get(f['properties'].get('osm_id'))
    if observation:
        bridges[-1]['status']='mapped_span_and_visual_bridge_confirmed_dimensions_unmeasured'
        bridges[-1]['view_record']='streetview_verified_20261022.json#'+observation['id']
        bridges[-1]['view_url']=observation['url']
report={'source':str(network_path),'candidate_source':str(route_path),'candidate_buffer_m':6,
        'buffer_is_design_search_tolerance':True,'bridges':bridges}
out=root/'results/territory/bridge_review.json';out.write_text(json.dumps(report,indent=2))
print(json.dumps(bridges,indent=2))
