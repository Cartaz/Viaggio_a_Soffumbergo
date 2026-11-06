"""Validate and mosaic all source DTM cells; sample the candidate route, ground only."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from pyproj import Transformer

root=Path(__file__).resolve().parents[1]
inventory=json.loads((root/'results/lidar_inventory.json').read_text())
out=root/'terrain/lidar_mosaic';out.mkdir(parents=True,exist_ok=True)
step=0.5
for tile in inventory['tiles']:
    if tile['header']['cellsize']!=step:raise ValueError('Mixed source grid spacing')
e0=min(t['header']['xllcenter'] for t in inventory['tiles'])
n0=max(t['header']['yllcenter']+(t['header']['nrows']-1)*step for t in inventory['tiles'])
east_max=max(t['header']['xllcenter']+(t['header']['ncols']-1)*step for t in inventory['tiles'])
north_min=min(t['header']['yllcenter'] for t in inventory['tiles'])
width=round((east_max-e0)/step)+1;height=round((n0-north_min)/step)+1
mosaic=np.lib.format.open_memmap(out/'height_m.npy',mode='w+',dtype='<f4',shape=(height,width))
mosaic[:]=np.nan
quality=np.lib.format.open_memmap(out/'source_margin_cells.npy',mode='w+',dtype='<u2',shape=(height,width));quality[:]=0
owners=np.lib.format.open_memmap(out/'source_index.npy',mode='w+',dtype='u1',shape=(height,width));owners[:]=0
reports=[];overlap_count=0;overlap_max_error=0.0
disagreeing_cells=0
for source_index,tile in enumerate(inventory['tiles'],1):
    path=Path(tile['path']);h=tile['header']
    data=np.loadtxt(path,skiprows=6,dtype=np.float32)
    if data.shape!=(int(h['nrows']),int(h['ncols'])):raise ValueError('Incorrect raster dimensions: '+str(path))
    valid=np.isfinite(data)&(data!=h['nodata_value'])
    col_float=(h['xllcenter']-e0)/step
    row_float=(n0-h['yllcenter']-(h['nrows']-1)*step)/step
    if abs(col_float-round(col_float))>1e-8 or abs(row_float-round(row_float))>1e-8:raise ValueError('Misaligned source grid')
    col,row=round(col_float),round(row_float)
    target=mosaic[row:row+data.shape[0],col:col+data.shape[1]]
    overlap=np.isfinite(target)&valid
    error=float(np.max(np.abs(target[overlap]-data[overlap]))) if overlap.any() else 0.0
    difference_count=int(np.count_nonzero(np.abs(target[overlap]-data[overlap])>0.001))
    disagreeing_cells+=difference_count
    overlap_count+=int(overlap.sum());overlap_max_error=max(overlap_max_error,error)
    # Overlapping source buffers may differ. Select the sample furthest inside
    # its source tile, retaining an original measured value rather than blending.
    margins=np.minimum(np.minimum(np.arange(data.shape[0])+1,np.arange(data.shape[0],0,-1))[:,None],
                       np.minimum(np.arange(data.shape[1])+1,np.arange(data.shape[1],0,-1))[None,:]).astype('<u2')
    old_quality=quality[row:row+data.shape[0],col:col+data.shape[1]]
    old_owners=owners[row:row+data.shape[0],col:col+data.shape[1]]
    choose=valid&((~np.isfinite(target))|(margins>old_quality))
    target[choose]=data[choose];old_quality[choose]=margins[choose];old_owners[choose]=source_index
    report={'name':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'valid_cells':int(valid.sum()),'nodata_cells':int((~valid).sum()),
            'height_min_max_m':[float(data[valid].min()),float(data[valid].max())] if valid.any() else None,
            'overlap_cells':int(overlap.sum()),'max_overlap_error_m':error,'overlap_cells_differing_over_1mm':difference_count}
    reports.append(report);print(json.dumps(report),flush=True)
mosaic.flush();quality.flush();owners.flush()
projection=Transformer.from_crs(4326,6708,always_xy=True)
route=json.loads(Path(inventory['route_path']).read_text(encoding='utf-8'))
sampled=[];sector_reports=[]
for feature in route['features']:
    geometry=feature['geometry'];parts=geometry['coordinates'] if geometry['type']=='MultiLineString' else [geometry['coordinates']]
    samples=[];missing=0
    for part in parts:
        coords=[projection.transform(*p[:2]) for p in part]
        for a,b in zip(coords,coords[1:]):
            count=max(1,math.ceil(math.dist(a,b)/2))
            for i in range(count):
                t=i/count;e=a[0]+t*(b[0]-a[0]);n=a[1]+t*(b[1]-a[1])
                x=(e-e0)/step;y=(n0-n)/step;ix,iy=math.floor(x),math.floor(y);dx,dy=x-ix,y-iy
                h=None
                if 0<=ix<width-1 and 0<=iy<height-1:
                    values=mosaic[iy:iy+2,ix:ix+2]
                    if np.isfinite(values).all():
                        h=float((1-dy)*((1-dx)*values[0,0]+dx*values[0,1])+dy*((1-dx)*values[1,0]+dx*values[1,1]))
                if h is None:missing+=1
                samples.append([e,n,h])
    grades=[]
    for a,b in zip(samples,samples[1:]):
        if a[2] is not None and b[2] is not None:
            distance=math.hypot(a[0]-b[0],a[1]-b[1])
            if distance>0.01:grades.append(abs(b[2]-a[2])/distance)
    sector=feature['properties'].get('sector')
    sampled.append({'sector':sector,'coordinates_ENH_m':samples})
    sector_reports.append({'sector':sector,'samples':len(samples),'missing_height_samples':missing,
                           'max_bare_ground_grade_percent':max(grades)*100 if grades else None,
                           'grade_p95_percent':float(np.percentile(grades,95))*100 if grades else None})
report={'tile_count':len(reports),'origin_E_N_m':[e0,n0],'step_m':step,'width':width,'height':height,
        'dtype':'little-endian float32, numpy .npy','height_datum':'source ellipsoidal elevations retained',
        'horizontal_crs':'EPSG:6708','tiles':reports,'overlap_cells_checked':overlap_count,
        'max_overlap_error_m':overlap_max_error,'overlap_cells_differing_over_1mm':disagreeing_cells,
        'overlap_policy':'original value from source with greatest distance from tile edge; lexical source order resolves ties',
        'overlap_heights_identical':disagreeing_cells==0,'seam_visual_review_required':disagreeing_cells>0,
        'resampling':False,'noise':False,'nodata_fill':False,
        'route_sectors':sector_reports,'candidate_route_alignment_verified':False,'road_surface_verified':False,
        'whole_mosaic_imported_in_unreal':False}
(out/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
(out/'candidate_route_ground_samples.json').write_text(json.dumps({'status':'bare ground sampled from candidate plan route; not a road','sectors':sampled},indent=2))
(root/'results/lidar_mosaic_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'complete':True,'width':width,'height':height,'overlaps':overlap_count,'max_overlap_error_m':overlap_max_error,'route_sectors':sector_reports}),flush=True)
