"""Join LiDAR anomaly clusters with the nearest documented Street View stations."""
import csv,json,math
from pathlib import Path
from pyproj import Transformer
root=Path(__file__).resolve().parents[1]
old=(Path(__file__).resolve().parents[1] / 'data/geography')
anomalies=list(csv.DictReader((root/'results/territory/route_terrain_anomalies.csv').open(encoding='utf-8-sig')))
views=list(csv.DictReader((old/'streetview_views.csv').open(encoding='utf-8-sig'),delimiter=';'))
observations={r['review_id']:r['description'] for r in csv.DictReader((old/'streetview_observations.csv').open(encoding='utf-8-sig'),delimiter=';')}
verified_path=root/'results/territory/streetview_verified_20261022.json'
verified={v['id']:v for v in json.loads(verified_path.read_text())['views']} if verified_path.exists() else {}
projection=Transformer.from_crs(4326,6708,always_xy=True)
for v in views:v['EN']=projection.transform(float(v['longitude']),float(v['latitude']))
groups=[]
for a in anomalies:
    p=[float(a['easting_m']),float(a['northing_m'])]
    found=next((g for g in groups if g['sector']==a['sector'] and math.dist(p,g['EN_m'])<60),None)
    if found:found['anomalies'].append(a)
    else:groups.append({'id':f'ROAD-{len(groups)+1:03}','sector':a['sector'],'EN_m':p,'anomalies':[a]})
for g in groups:
    closest=min(views,key=lambda v:math.dist(g['EN_m'],v['EN']))
    g['nearest_review_id']=closest['review_id'];g['distance_to_view_m']=math.dist(g['EN_m'],closest['EN'])
    g['existing_observation']=observations.get(closest['review_id'])
    g['streetview_url']='https://www.google.com/maps/@?api=1&map_action=pano&pano='+closest['pano_id']+'&viewpoint='+closest['latitude']+','+closest['longitude']+'&heading='+closest['heading_deg']
    g['image_date_recorded']=closest['image_date']
    g['new_view_verified']=closest['review_id'] in verified
    if g['new_view_verified']:
        g['verified_view_record']='streetview_verified_20261022.json#'+closest['review_id']
        g['verification_scope']='Nearest station visually reviewed; anomaly feature not automatically classified by proximity'
(root/'results/territory/road_review_groups.json').write_text(json.dumps(groups,indent=2),encoding='utf-8')
print(json.dumps([{k:g[k] for k in ['id','sector','EN_m','nearest_review_id','distance_to_view_m','existing_observation','streetview_url']} for g in groups],ensure_ascii=False))
