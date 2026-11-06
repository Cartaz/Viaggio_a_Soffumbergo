"""OSM mapped cover/exclusions aligned exactly to the LiDAR Landscape grid."""
import json
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from pyproj import Transformer
import shapely
from shapely.geometry import shape, box

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(Path(__file__).resolve().parents[1] / 'data/geography')
OLD=(Path(__file__).resolve().parents[1] / 'data/geography')
OUT=ROOT/'terrain/valle_first'
m=json.loads((OUT/'manifest.json').read_text())
e0,n0,_=m['origin_ENH_m'];step=m['spacing_m'];n=m['samples_per_side']
roi=box(e0,n0-(n-1)*step,e0+(n-1)*step,n0)
projection=Transformer.from_crs(4326,6708,always_xy=True)
groups={k:[] for k in ['forest','meadow','scrub','buildings','roads','paths']}
sources=[]
files=[SOURCE/'osm_circuit_environment.geojson',SOURCE/'osm_survey.geojson',
       OLD/'osm_regional_roads_20261020.geojson']
for path in files:
    if not path.exists():
        raise FileNotFoundError(path)
    raw=path.read_bytes();data=json.loads(raw)
    sources.append({'path':str(path),'sha256':hashlib.sha256(raw).hexdigest()})
    for feature in data['features']:
        if not feature.get('geometry'):continue
        props=feature.get('properties',{});tags=props.get('tags',props)
        geometry=shapely.transform(shape(feature['geometry']),projection.transform,interleaved=False)
        if not geometry.is_valid:geometry=shapely.make_valid(geometry)
        if not geometry.intersects(roi.buffer(30)):continue
        if tags.get('building'):
            groups['buildings'].append(geometry)
        if tags.get('landuse')=='forest' or tags.get('natural')=='wood':
            groups['forest'].append(geometry)
        if tags.get('landuse') in ('meadow','grass') or tags.get('natural')=='grassland':
            groups['meadow'].append(geometry)
        if tags.get('natural')=='scrub':groups['scrub'].append(geometry)
        highway=tags.get('highway')
        if highway in ('footway','path','steps','cycleway','bridleway'):
            groups['paths'].append(geometry)
        elif highway and highway not in ('street_lamp','bus_stop','crossing','traffic_signals','give_way'):
            if geometry.geom_type in ('LineString','MultiLineString','Polygon','MultiPolygon'):
                groups['roads'].append(geometry)

unions={k:shapely.union_all(v) for k,v in groups.items()}
east,north=np.meshgrid(e0+np.arange(n)*step,n0-np.arange(n)*step)
mask=np.zeros((n,n),dtype=np.uint8)
for name,value in [('meadow',2),('scrub',3),('forest',1)]:
    if not unions[name].is_empty:mask[shapely.contains_xy(unions[name],east,north)]=value
# These are conservative DESIGN setbacks from mapped geometry, not surveyed widths.
exclusions=shapely.union_all([unions['buildings'].buffer(5),unions['roads'].buffer(8),unions['paths'].buffer(6)])
excluded=shapely.intersects_xy(exclusions,east,north)
mask[excluded]=0
mask.tofile(OUT/'vegetation_mask.bin')
palette=np.array([[92,87,78],[40,98,42],[170,177,85],[104,139,64]],dtype=np.uint8)
image=palette[mask];image[excluded]=[168,80,68]
Image.fromarray(image).save(OUT/'vegetation_mask.png')
metadata={
 'width':n,'height':n,'spacing_cm':step*100,'origin_cm':[0,0,0],
 'classes':{'0':'unknown_or_excluded_no_spawn','1':'OSM forest/wood','2':'OSM meadow/grassland','3':'OSM scrub'},
 'sources':sources,'projection_description':projection.description,'projection_accuracy_m':projection.accuracy,
 'mapped_features':{k:len(v) for k,v in groups.items()},
 'cells_per_class':{str(i):int(np.count_nonzero(mask==i)) for i in range(4)},
 'setbacks_m_design_not_survey':{'building':5,'road_centerline':8,'path_centerline':6},
 'mask_sha256':hashlib.sha256(mask.tobytes()).hexdigest(),
 'tree_positions_observed':False,'species_observed':False,
 'terrain_source':'manifest.json','unknown_cover_policy':'no vegetation',
 'osm_license':'ODbL 1.0, OpenStreetMap contributors',
 'geometry_limitations':'OSM approximate mapped coverage; setbacks are provisional design parameters'
}
(OUT/'vegetation_mask.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
print(json.dumps(metadata))
