"""Build a provenance-preserving streamed circuit corridor from registered raw DTM.

Output contains ground only, plus OSM candidate inspection lines. Originals are
checksum-verified on every run. Null samples stay holes; no road is inferred.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

from catalog_circuit_dtm import read_header
from coffa.dtm_mosaic import Mosaic, corridor_sectors, masked_lod_error
from register_dtm import sha256_file

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT/'data/geography/circuit_dtm_catalog_20261020.json'
ROUTE = ROOT/'data/geography/circuito_osm_candidate_20261020.geojson'
CONFIG = ROOT/'data/config/circuit_3d.json'


def encode(doc):
    return (json.dumps(doc,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode('utf-8')


def atomic_write(path, content):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_bytes(content)
    tmp.replace(path)


def load_sources(folder,catalog):
    import numpy as np
    arrays = []
    names = {t['filename'] for t in catalog['tiles']}
    if {p.name for p in folder.glob('*.asc')} != names:
        raise ValueError('DTM input files differ from the registered catalog; recatalog explicitly')
    for tile in catalog['tiles']:
        path = folder/tile['filename']
        if sha256_file(path) != tile['sha256']:
            raise ValueError('DTM checksum changed: '+path.name)
        with path.open('r',encoding='ascii') as stream:
            h = read_header(stream)
            values = np.loadtxt(stream,dtype=np.float32)
        west,south = h['xllcenter']-.25,h['yllcenter']-.25
        if [west,south,west+900,south+840] != tile['bounds_EN_m']:
            raise ValueError('DTM bounds differ from catalog')
        if values.shape != (1680,1800) or not np.isfinite(values).all():
            raise ValueError('Invalid raster after checksum verification')
        arrays.append(values)
    return arrays


def projected_route(origin):
    from pyproj import Transformer,network
    network.set_network_enabled(False)
    projection = Transformer.from_crs('EPSG:4326','EPSG:6708',always_xy=True,allow_ballpark=False)
    source = json.loads(ROUTE.read_text(encoding='utf-8'))
    route = []
    for feature in source['features']:
        raw = [projection.transform(*p[:2]) for p in feature['geometry']['coordinates']]
        points = [raw[0]]
        for a,b in zip(raw,raw[1:]):
            count = max(1,math.ceil(math.dist(a,b)/2))
            points.extend([(a[0]+i/count*(b[0]-a[0]),a[1]+i/count*(b[1]-a[1])) for i in range(1,count+1)])
        route.append({'sector':feature['properties']['sector'],
                      'xz_m':[[e-origin[0],origin[1]-n] for e,n in points]})
    return route,projection.description


def build(folder,output):
    import numpy as np
    if not output.resolve().is_relative_to(ROOT/'build'):
        raise ValueError('Terrain derivatives must remain under ignored build/')
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    origin = config['origin_ENH_m']
    if config['sector_size_m'] != 128 or config['terrain_step_m'] != 2 or config['lod_strides'] != [1,2,4]:
        raise ValueError('Unsupported sector layout')
    fingerprints = {str(p.relative_to(ROOT)):sha256_file(p) for p in
                    [CONFIG,CATALOG,ROUTE,Path(__file__),ROOT/'tools/coffa/dtm_mosaic.py']}
    build_id = hashlib.sha256(encode(fingerprints)).hexdigest()[:20]
    arrays = load_sources(folder,catalog)
    mosaic = Mosaic(catalog['tiles'],arrays,origin,config['valle_primary_tiles'],config['valle_region_local_xz_m'])
    route,operation = projected_route(origin)
    # +1 m conservatively covers unsampled positions between the <=2 m route samples.
    positions = corridor_sectors([p for f in route for p in f['xz_m']],128,config['corridor_half_width_m']+1)
    a,b,c,d = config['valle_region_local_xz_m']
    positions = sorted(set(positions)|{(x,z) for z in range(b,d,128) for x in range(a,c,128)},key=lambda p:(p[1],p[0]))
    entries,cache = [],{}
    for index,(x,z) in enumerate(positions):
        xx,zz = np.meshgrid(np.arange(x-2,x+131,2),np.arange(z-2,z+131,2))
        hh,source,spread = mosaic.sample(xx,zz)
        center = hh[1:-1,1:-1]
        valid = np.isfinite(center)
        def derivative(before,after):
            left,right = np.isfinite(before),np.isfinite(after)
            return np.where(left&right,(after-before)/4,
                            np.where(right,(after-center)/2,np.where(left,(center-before)/2,0)))
        dx,dz = derivative(hh[1:-1,:-2],hh[1:-1,2:]),derivative(hh[:-2,1:-1],hh[2:,1:-1])
        norm = np.sqrt(dx*dx+dz*dz+1)
        normals = np.stack((-dx/norm,1/norm,-dz/norm),axis=-1)
        normals[~valid] = (0,1,0)
        heights = [round(float(h),4) if math.isfinite(h) else None for h in center.ravel()]
        errors = [masked_lod_error(heights,65,s) for s in [1,2,4]]
        chunk = {'id':f'{x}_{z}','offset_xz_m':[x,z],'side':65,'step_m':2,
                 'heights_m':heights,'normals':np.round(normals,6).reshape(-1,3).tolist(),
                 'source_ids':source[1:-1,1:-1].ravel().tolist(),
                 'lod_max_error_m':errors,'skirt_depth_m':max(errors)+1,
                 'missing_vertices':int((~valid).sum()),'max_source_spread_m':float(spread[1:-1,1:-1].max())}
        encoded = encode(chunk)
        relative = f'datasets/{build_id}/{chunk["id"]}.json'
        atomic_write(output/relative,encoded)
        overview_ids = [r*65+c for r in range(0,65,4) for c in range(0,65,4)]
        overview = {**{k:chunk[k] for k in ['id','offset_xz_m','skirt_depth_m']},
                    'side':17,'step_m':8,'heights_m':[heights[i] for i in overview_ids],
                    'normals':[chunk['normals'][i] for i in overview_ids]}
        entries.append({'id':chunk['id'],'offset_xz_m':[x,z],'path':relative,
                        'sha256':hashlib.sha256(encoded).hexdigest(),'overview':overview,
                        'missing_vertices':chunk['missing_vertices'],
                        'lod_max_error_m':errors,'max_source_spread_m':chunk['max_source_spread_m']})
        cache[(x,z)] = chunk
        if index % 50 == 0:
            print(f'Generated {index+1}/{len(positions)} sectors',flush=True)

    def mesh_height(x,z):
        sector = cache.get((math.floor(x/128)*128,math.floor(z/128)*128))
        if sector is None:
            raise ValueError('OSM candidate outside generated corridor')
        u,v = (x-sector['offset_xz_m'][0])/2,(z-sector['offset_xz_m'][1])/2
        c,r = min(int(u),63),min(int(v),63)
        u,v = u-c,v-r
        a,b,d,e = [sector['heights_m'][k] for k in [r*65+c,r*65+c+1,(r+1)*65+c,(r+1)*65+c+1]]
        if any(h is None for h in (a,b,d,e)):
            raise ValueError('OSM candidate touches an uncovered terrain cell')
        return a+(b-a)*u+(d-a)*v if u+v <= 1 else e+(d-e)*(1-u)+(b-e)*(1-v)

    for feature in route:
        points = np.array(feature.pop('xz_m'))
        height,sources,spread = mosaic.sample(points[:,0],points[:,1])
        if not np.isfinite(height).all():
            raise ValueError('Missing ground on OSM candidate; no inferred heights allowed')
        feature['points_m'] = [[float(x),mesh_height(x,z),float(z)] for x,z in points]
        feature['source_ids'] = sources.tolist()
        feature['source_spread_m'] = np.round(spread,6).tolist()
        feature['selected_DTM_heights_local_m'] = np.round(height,6).tolist()
    # Valle's fixed 2m field remains numerically identical; reuse its content metadata.
    valle_path = ROOT/'build/valle/valle_scene.json'
    valle = json.loads(valle_path.read_text(encoding='utf-8'))
    valle_error = max(abs(h-q) for s in valle['sectors']
                      for h,q in zip(s['heights_m'],cache[tuple(s['offset_xz_m'])]['heights_m']))
    if valle_error > .0001:
        raise ValueError(f'Valle terrain changed by {valle_error} m')
    seams = 0
    for (x,z),s in cache.items():
        for dx,dz in [(128,0),(0,128)]:
            neighbor = cache.get((x+dx,z+dz))
            if neighbor:
                for i in range(65):
                    a,b = (i*65+64,i*65) if dx else (64*65+i,i)
                    for field in ['heights_m','normals','source_ids']:
                        if s[field][a] != neighbor[field][b]:
                            raise ValueError('Nonidentical shared sector edge')
                seams += 1
    manifest = {'schema_version':1,'prototype':'Circuito 3D 0.1','build_id':build_id,
                'axes':'+X east, +Y up, +Z south','horizontal_crs':'EPSG:6708',
                'vertical_reference':'ellipsoidal_as_declared_Ell_DTM','datum_conversion_applied':False,
                'origin_ENH_m':origin,'source_fingerprints':fingerprints,
                'source_tiles':mosaic.tiles,'config':config,'sectors':entries,'route':route,
                'valle_content':{k:valle[k] for k in ['buildings','roads','anchors']},
                'valle_source_sha256':sha256_file(valle_path),
                'road_surface_verified':False,'redistribution_status':'local_only_pending_rights_review'}
    atomic_write(output/'manifest.json',encode(manifest))
    (ROOT/'build/.gdignore').touch()
    report = {'build_id':build_id,'manifest_sha256':sha256_file(output/'manifest.json'),
              'sector_count':len(entries),'shared_edges_checked':seams,'shared_edge_error_m':0,
              'valle_height_max_delta_m':valle_error,'source_tile_count':len(mosaic.tiles),
              'sectors_with_missing_vertices':sum(s['missing_vertices']>0 for s in entries),
              'missing_vertices_including_shared_edges':sum(s['missing_vertices'] for s in entries),
              'lod_max_error_m':[max(s['lod_max_error_m'][i] for s in entries) for i in range(3)],
              'max_sampled_source_spread_m':max(s['max_source_spread_m'] for s in entries),
              'route_samples':sum(len(f['points_m']) for f in route),
              'route_samples_with_multiple_distinct_sources':sum(v>1e-6 for f in route for v in f['source_spread_m']),
              'mosaic_policy':config['mosaic_policy'],'road_surface_verified':False}
    atomic_write(output/'generation_report.json',encode(report))
    print(json.dumps(report,indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir',required=True,type=Path)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'build/circuit')
    args = parser.parse_args()
    build(args.input_dir,args.output_dir)
