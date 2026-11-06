"""Map valid LiDAR coverage and flag steep bare-ground sections for road review."""
import csv
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from pyproj import Transformer

root=Path(__file__).resolve().parents[1]
source=root/'terrain/lidar_mosaic'
manifest=json.loads((source/'manifest.json').read_text())
sectors=json.loads((source/'candidate_route_ground_samples.json').read_text())['sectors']
terrain=np.load(source/'height_m.npy',mmap_mode='r')
report_dir=root/'results/territory';report_dir.mkdir(parents=True,exist_ok=True)
to_gps=Transformer.from_crs(6708,4326,always_xy=True)
anomalies=[]
for sector in sectors:
    for i,(a,b) in enumerate(zip(sector['coordinates_ENH_m'],sector['coordinates_ENH_m'][1:])):
        distance=math.hypot(b[0]-a[0],b[1]-a[1])
        if distance<0.1 or a[2] is None or b[2] is None:continue
        grade=100*(b[2]-a[2])/distance
        if abs(grade)>20:
            e=(a[0]+b[0])/2;n=(a[1]+b[1])/2;lon,lat=to_gps.transform(e,n)
            anomalies.append({'sector':sector['sector'],'segment_index':i,'easting_m':e,'northing_m':n,
                              'longitude':lon,'latitude':lat,'bare_ground_grade_percent':grade,
                              'review':'Check mapped alignment, bridge/wall/culvert and actual road profile; no automatic correction'})
with (report_dir/'route_terrain_anomalies.csv').open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.DictWriter(f,fieldnames=list(anomalies[0]) if anomalies else ['sector']);writer.writeheader();writer.writerows(anomalies)
stride=10;sample=np.asarray(terrain[::stride,::stride],dtype=float)
valid=np.isfinite(sample);lo,hi=np.nanmin(sample),np.nanmax(sample)
safe=np.where(valid,sample,lo)
dy,dx=np.gradient(safe,manifest['step_m']*stride)
norm=np.sqrt(1+dx*dx+dy*dy)
light=np.clip((-0.5*dx-0.5*dy+0.7071)/norm,0.15,1)
t=np.clip((safe-lo)/(hi-lo),0,1)
rgb=np.stack([80+80*t,111+65*t,65+80*t],axis=-1)*(0.5+light[...,None]*0.7)
rgb=np.clip(rgb,0,255).astype('u1');rgb[~valid]=[231,231,231]
padding=85;footer=100
image=Image.new('RGB',(rgb.shape[1]+padding*2,rgb.shape[0]+padding+footer),'white')
image.paste(Image.fromarray(rgb),(padding,padding))
draw=ImageDraw.Draw(image)
font_path=Path('C:/Windows/Fonts/segoeui.ttf')
font=ImageFont.truetype(str(font_path),20);small=ImageFont.truetype(str(font_path),15)
draw.text((padding,18),'LiDAR disponibile e tracciato candidato',fill='#202b2d',font=font)
e0,n0=manifest['origin_E_N_m'];pixel=manifest['step_m']*stride
xy=lambda p:(padding+(p[0]-e0)/pixel,padding+(n0-p[1])/pixel)
for sector in sectors:
    coords=[xy(p) for p in sector['coordinates_ENH_m']]
    if len(coords)>1:draw.line(coords,fill='#135fd7',width=3)
    if coords:draw.text(coords[len(coords)//2],sector['sector'],fill='#101010',font=font,stroke_width=2,stroke_fill='white')
for anomaly in anomalies:
    x,y=xy((anomaly['easting_m'],anomaly['northing_m']))
    draw.ellipse((x-3,y-3,x+3,y+3),fill='#ec6428')
for tick in range(0,int(rgb.shape[1]*pixel),1000):
    x=padding+tick/pixel
    draw.text((x-20,padding-25),str(round(e0+tick)),font=small,fill='#333333')
for tick in range(0,int(rgb.shape[0]*pixel),1000):
    y=padding+tick/pixel
    draw.text((4,y-8),str(round(n0-tick)),font=small,fill='#333333')
y=padding+rgb.shape[0]+16
draw.text((padding,y),'Blu: percorso OSM candidato. Arancio: suolo con pendenza locale oltre il 20%.',fill='#333333',font=small)
draw.text((padding,y+23),'Grigio: fuori dalle celle disponibili. EPSG:6708; quote ellissoidiche. Nessuna strada validata.',fill='#333333',font=small)
draw.text((padding,y+46),'41 tessere a 0,5 m; questa immagine mostra un campione ogni 5 m. Fonti: DTM locali e OSM.',fill='#333333',font=small)
image.save(report_dir/'coverage_route.png')
summary={'source_tiles':manifest['tile_count'],'source_cells_valid':sum(t['valid_cells'] for t in manifest['tiles']),
         'source_nodata_cells':sum(t['nodata_cells'] for t in manifest['tiles']),
         'route_ground_samples':sum(s['samples'] for s in manifest['route_sectors']),
         'missing_route_heights':sum(s['missing_height_samples'] for s in manifest['route_sectors']),
         'segments_over_20_percent_grade':len(anomalies),'route_alignment_verified':False,
         'source_overlap_max_difference_m':manifest['max_overlap_error_m'],'full_world_imported':False}
(root/'results/territory_review.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary))
