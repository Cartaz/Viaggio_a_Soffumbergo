"""Catalogue local LiDAR footprints against the candidate route, without inventing data."""
import hashlib
import json
from pathlib import Path
from pyproj import Transformer
import shapely
from shapely.geometry import box,shape,LineString

root=Path(__file__).resolve().parents[1]
source=(Path(__file__).resolve().parents[1] / 'data/lidar/raw_20261020')
tiles=[];footprints=[]
for path in sorted(source.glob('*.asc')):
    header={}
    with path.open(encoding='ascii') as stream:
        for _ in range(6):
            key,value=stream.readline().split();header[key.lower()]=float(value)
    step=header['cellsize'];e=header.get('xllcenter',header.get('xllcorner',0)+step/2)
    n=header.get('yllcenter',header.get('yllcorner',0)+step/2)
    bounds=[e-step/2,n-step/2,e+(header['ncols']-0.5)*step,n+(header['nrows']-0.5)*step]
    footprints.append(box(*bounds))
    tiles.append({'path':str(path),'bytes':path.stat().st_size,'header':header,'footprint_EN_m':bounds})
coverage=shapely.union_all(footprints)
route_path=(Path(__file__).resolve().parents[1] / 'data/geography/circuito_osm_candidate_20261020.geojson')
route_data=json.loads(route_path.read_text(encoding='utf-8'))
projection=Transformer.from_crs(4326,6708,always_xy=True)
route_segments=[]
for feature in route_data['features']:
    line=shapely.transform(shape(feature['geometry']),projection.transform,interleaved=False)
    length=line.length
    # Preserve every traversal, including an out-and-back over the same segment.
    parts=list(line.geoms) if line.geom_type=='MultiLineString' else [line]
    covered=sum(LineString([a,b]).intersection(coverage).length for part in parts for a,b in zip(part.coords,list(part.coords)[1:]))
    route_segments.append({'sector':feature['properties'].get('sector'),'length_m':length,
                           'within_tile_footprints_m':covered,'uncovered_m':length-covered})
report={'status':'header_and_footprint_inventory_only','tile_count':len(tiles),'tiles':tiles,
        'file_bytes_total':sum(t['bytes'] for t in tiles),'footprint_union_area_m2':coverage.area,
        'bounds_EN_m':list(coverage.bounds),'horizontal_crs':'EPSG:6708 from existing provenance',
        'vertical_datum':'ellipsoidal, to retain from source metadata',
        'route_path':str(route_path),'route_sha256':hashlib.sha256(route_path.read_bytes()).hexdigest(),
        'route_segments':route_segments,'route_alignment_verified':False,
        'coverage_of_valid_elevations_verified':False,'nodata_cells_scanned':False,
        'seams_checked':False,'whole_circuit_imported':False,
        'limitations':'Tile footprints do not certify valid cells, drivable road surface or itinerary alignment'}
(root/'results/lidar_inventory.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['tile_count','file_bytes_total','bounds_EN_m','route_segments']}))
