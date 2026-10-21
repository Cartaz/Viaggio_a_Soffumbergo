"""Regenerate coded visual placeholders from observations, OSM and local ground.

No imagery or original raster is written. Placement from Street View is a design
estimate at the observed panorama, never a perspective-derived measurement.
"""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np
from pyproj import Transformer, network
import shapely
from shapely import Point, LineString, Polygon, box
from shapely.affinity import rotate, translate
from shapely.ops import transform

from build_circuit_3d import atomic_write, encode
from coffa.environment import observation_code, parse_feature, recipe, validate_object
from coffa.road_construction import road_footprint
from coffa.road_shoulders import terrain_height

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT/'data/geography'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(name):
    return list(csv.DictReader((GEO/name).read_text(encoding='utf-8').splitlines(), delimiter=';'))


def footprint(obj):
    parts = []
    for p in obj['primitives']:
        w, _, d = p['size_m']
        x, _, z = p['center_m']
        parts.append(box(x-w/2, z-d/2, x+w/2, z+d/2))
    return translate(rotate(shapely.union_all(parts), -obj['yaw_deg'], origin=(0, 0)),
                     obj['position_m'][0], obj['position_m'][2])


def baseline(project, spacing=250):
    result, start = [], 0.0
    source = json.loads((GEO/'circuito_osm_candidate_20261020.geojson').read_bytes())
    for f in source['features']:
        line = LineString([project(*p) for p in f['geometry']['coordinates']])
        n = max(1, round(line.length/spacing))
        for i in range(n+1):
            s = line.length*i/n
            p = line.interpolate(s)
            result.append({'id':f'SV-{len(result)+1:03}', 'sector':f['properties']['sector'],
                           'station_m':round(start+s, 3), 'target_EN_m':[p.x, p.y]})
        start += line.length
    return result, start


def catalog_html(catalog):
    # Self-contained, offline, no Google media embeds or remote scripts/fonts.
    data = json.dumps(catalog, ensure_ascii=False).replace('<', '\\u003c')
    return ('''<!doctype html><html lang="it"><meta charset="utf-8">
<title>Catalogo dei segnaposto · Soffumbergo</title><style>
body{font:16px system-ui;background:#f4f2eb;color:#25332f;margin:32px auto;max-width:1100px;padding:0 20px}
h1{font-size:30px}input,select,button{font:inherit;padding:10px;margin:4px;border:1px solid #aaa;border-radius:6px}
article{background:white;padding:18px;margin:12px 0;border-radius:8px;border-left:5px solid #6d876c}
code{font-weight:bold;color:#435d53}small{display:block;color:#59645e;margin-top:8px}pre{white-space:pre-wrap;font-size:12px}
a{color:#285a79}#summary{margin:18px 0}label{display:inline-block}</style>
<h1>Catalogo dei segnaposto</h1><p>Codici stabili, descrizioni e ricette per la ricostruzione.
Le forme sono provvisorie. Posizioni da Street View e altezze non sono misure rilevate.</p>
<label>Cerca codice o descrizione <input id="search" type="search"></label>
<label>Categoria <select id="category"><option value="">Tutte</option></select></label>
<div id="summary"></div><main id="items"></main><script>
const data=CATALOG_DATA;const search=document.querySelector('#search');
const category=document.querySelector('#category');const items=document.querySelector('#items');
const labels={osm_plan_geometry_not_surveyed:'Posizione da pianta OSM, da verificare',estimated_visual_group_locator_not_metric_location:'Collocazione visiva approssimativa',design_assumption:'Forma e dimensioni provvisorie di progetto',osm_plan_rectangle_height_assumed:'Box da pianta OSM, altezza provvisoria',visible_blockout:'Visibile nel prototipo',deferred_road_or_shoulder_conflict:'Da rivedere: interferenza con strada o raccordi',deferred_no_safe_ground_placement:'Da collocare: manca una posizione utilizzabile'};
for(const [key,value] of Object.entries(data.categories)){const o=document.createElement('option');o.value=key;o.textContent=value.label;category.append(o)}
function render(){const query=search.value.toLocaleLowerCase('it');const found=data.objects.filter(o=>(!category.value||o.category===category.value)&&JSON.stringify([o.code,o.description,o.sector]).toLocaleLowerCase('it').includes(query));
document.querySelector('#summary').textContent=found.length+' elementi · '+data.coverage.review_count+' postazioni osservate · copertura puntuale, non censimento continuo';items.replaceChildren();
for(const o of found.slice(0,150)){const a=document.createElement('article');const c=document.createElement('code');c.textContent=o.code;a.append(c);const p=document.createElement('p');p.textContent=o.description;a.append(p);
const s=document.createElement('small');s.textContent='Settore '+o.sector+' · '+labels[o.position_status]+' · '+labels[o.dimensions_status]+' · '+labels[o.runtime_status];a.append(s);
for(const src of o.source){const link=document.createElement('a');link.href=src.url;link.textContent=src.kind==='osm'?'OpenStreetMap':'Vista '+src.review_id;link.target='_blank';link.rel='noopener noreferrer';a.append(link,document.createTextNode('  '))}
const details=document.createElement('details');const title=document.createElement('summary');title.textContent='Ricetta completa per rigenerare';const pre=document.createElement('pre');pre.textContent=JSON.stringify(o,null,2);details.append(title,pre);a.append(details);items.append(a)}
if(found.length>150){const p=document.createElement('p');p.textContent='Mostrati i primi 150 risultati. Usa la ricerca per restringere il catalogo.';items.append(p)}}
search.addEventListener('input',render);category.addEventListener('change',render);render();</script></html>''').replace('CATALOG_DATA', data).encode('utf-8')


def build():
    network.set_network_enabled(False)
    projection = Transformer.from_crs(4326, 6708, always_xy=True, allow_ballpark=False)
    inverse = Transformer.from_crs(6708, 4326, always_xy=True, allow_ballpark=False)
    folder = ROOT/'build/circuit'
    source_manifest = folder/'construction_manifest.json'
    manifest = json.loads(source_manifest.read_bytes())
    config_path = ROOT/'data/config/circuit_environment.json'
    config = json.loads(config_path.read_bytes())
    categories = config['categories']
    bindings = config.get('landmark_bindings', [])
    by_osm = {b['osm_id']:b for b in bindings}
    origin = manifest['origin_ENH_m']
    if origin != [375920, 5112728, 720] or manifest['horizontal_crs'] != 'EPSG:6708':
        raise ValueError('Unexpected coordinate frame')
    def local(lon, lat, z=None):
        e, n = projection.transform(lon, lat)
        return e-origin[0], origin[1]-n
    chunks, chunk_ids = {}, {}
    for e in manifest['sectors']:
        path = folder/e['path']
        if sha(path) != e['sha256']:
            raise ValueError('Ground chunk changed')
        key = tuple(e['offset_xz_m'])
        chunks[key], chunk_ids[key] = json.loads(path.read_bytes()), e['id']
    construction = manifest['engineering_construction']
    profile = np.asarray(construction['profile_points_m'])
    c = construction['report']['config']
    delta = np.diff(profile[:, [0, 2]], axis=0)
    tangent = delta/np.linalg.norm(delta, axis=1)[:, None]
    angles = np.degrees(np.arccos(np.clip((tangent*np.roll(tangent, 1, axis=0)).sum(axis=1), -1, 1)))
    aprons = np.where((angles >= c['corner_apron_min_degrees']) & (angles <= c['corner_apron_max_degrees']))[0]
    road = road_footprint(profile, c['width_m'], aprons, c['corner_apron_radius_m'])
    shoulders = json.loads((folder/'shoulders.json').read_bytes())
    margin = shoulders['config']['width_m']+config['road_and_shoulder_margin_m']
    protected = road.buffer(margin+0.002)
    route_lines = [LineString([(p[0], p[2]) for p in r['points_m']]) for r in manifest['route']]
    route = shapely.union_all(route_lines)
    baseline_rows, length = baseline(projection.transform, config['baseline_spacing_target_m'])
    queue = {r['id']:r for r in baseline_rows}
    # Four additional physical stations on the outgoing Valle spur; incoming pass reuses them.
    for i, s in enumerate([55, 110, 165, 220]):
        p = route_lines[3].interpolate(s)
        queue[f'SV-V{i+1:02}'] = {'id':f'SV-V{i+1:02}', 'sector':'V',
                                'station_m':round(baseline_rows[46]['station_m']+s, 3),
                                'target_EN_m':[p.x+origin[0], origin[1]-p.y]}
    views = defaultdict(list)
    for v in rows('streetview_views.csv'):
        v = dict(v, heading_deg=float(v['heading_deg']), latitude=float(v['latitude']), longitude=float(v['longitude']))
        v['url'] = ('https://www.google.com/maps/@?api=1&map_action=pano&pano='+v['pano_id']+
                    '&viewpoint='+str(v['latitude'])+','+str(v['longitude'])+'&heading='+str(v['heading_deg']))
        views[v['review_id']].append(v)
    observations = rows('streetview_observations.csv')
    if set(queue) != {r['review_id'] for r in observations} or set(views) != set(queue):
        raise ValueError('Queue, observed views and descriptions must match')
    reviews, max_snap = [], 0
    for obs in observations:
        q = queue[obs['review_id']]
        p = projection.transform(views[q['id']][0]['longitude'], views[q['id']][0]['latitude'])
        snap = math.dist(p, q['target_EN_m'])
        if snap > 30:
            raise ValueError('Panorama snapped too far from requested route station: '+q['id'])
        max_snap = max(max_snap, snap)
        reviews.append({**q, 'description':obs['description'], 'views':views[q['id']],
                        'panorama_offset_from_target_m':round(snap, 3),
                        'status':'visually_observed_station_not_continuous_interval'})
    review_lookup = {r['id']:r for r in reviews}
    objects, occupied, deferred_sources = [], [], []
    osm = json.loads((GEO/'osm_circuit_environment.geojson').read_bytes())
    existing = {b['id'] for b in manifest['valle_content']['buildings']}
    osm_ids = set()
    # OSM gives plan geometry. A minimum enclosing rectangle is explicitly an approximation.
    for f in osm['features']:
        props = f['properties']
        if 'building' not in props or f['geometry']['type'] != 'Polygon':
            continue
        poly = transform(local, shapely.geometry.shape(f['geometry']))
        if not poly.is_valid or poly.area < 1:
            deferred_sources.append({'osm_id':f['id'], 'reason':'invalid_or_degenerate_plan'})
            continue
        if poly.distance(route) > config['building_corridor_m'] and f['id'] not in existing:
            continue
        rect = poly.minimum_rotated_rectangle
        coords = list(rect.exterior.coords)
        a, b, d = np.asarray(coords[0]), np.asarray(coords[1]), np.asarray(coords[2])
        width, depth = float(np.linalg.norm(b-a)), float(np.linalg.norm(d-b))
        center = rect.centroid
        heights = terrain_height(chunks, [p[0] for p in coords[:4]]+[center.x],
                                  [p[1] for p in coords[:4]]+[center.y])
        if not np.isfinite(heights).all():
            deferred_sources.append({'osm_id':f['id'], 'reason':'incomplete_ground_at_box_corners'})
            continue
        sector = min(range(len(route_lines)), key=lambda i:poly.distance(route_lines[i]))
        binding = by_osm.get(f['id'])
        category = binding['category'] if binding else 'building'
        prototype = categories[category]
        height = prototype['size_m'][1]
        # Base penetrates the lowest corner; top clears the highest. No false measured height.
        base, top = float(heights.min())-.25, float(heights.max())+height
        yaw = math.degrees(math.atan2(-(b-a)[1], (b-a)[0]))
        label = props.get('name') or {'church':'Chiesa', 'house':'Abitazione', 'shed':'Annesso', 'garage':'Garage'}.get(props['building'], 'Edificio')
        if binding:
            label = binding['name']
        obj = {'code':'PH-'+prototype['code']+'-OSM-'+f['id'].replace('way/', 'W').replace('node/', 'N'),
               'osm_id':f['id'], 'category':category, 'family':'edifici',
               'description':label+' — sagoma OSM semplificata a box, facciata e altezza da elaborare.',
               'sector':manifest['route'][sector]['sector'],
               'position_m':[center.x, base, center.y], 'yaw_deg':yaw,
               'primitives':[{'kind':'box', 'size_m':[width, top-base, depth],
                              'center_m':[0, (top-base)/2, 0], 'color':prototype['color']}],
               'source':[{'kind':'osm', 'url':'https://www.openstreetmap.org/'+f['id']}],
               'position_status':'osm_plan_geometry_not_surveyed',
               'dimensions_status':'osm_plan_rectangle_height_assumed', 'collision_enabled':False,
               'context_reviews':[], 'runtime_status':'visible_blockout'}
        if binding:
            obj['visual_to_osm_match_status'] = 'contextual_inference_not_metric_survey'
            obj['visual_to_osm_match_basis'] = binding['basis']
        # Don't relocate mapped houses or shrink them to disguise a candidate-road conflict.
        if rect.intersects(protected):
            obj['runtime_status'] = 'deferred_road_or_shoulder_conflict'
        else:
            occupied.append(rect)
        objects.append(obj)
        osm_ids.add(f['id'])
    buildings = [o for o in objects if 'osm_id' in o]
    mapped = {o['osm_id']:o for o in buildings}
    building_points = np.array([[o['position_m'][0], o['position_m'][2]] for o in buildings])
    obstacle = shapely.union_all(occupied).buffer(.4)
    by_code, aliases = {}, []
    side_names = {'L':'sinistra', 'R':'destra', 'F':'fronte'}
    for obs in observations:
        r = review_lookup[obs['review_id']]
        v = r['views'][0]
        px, pz = local(v['longitude'], v['latitude'])
        for token in obs['features'].split(','):
            category, side, heading, bearing = parse_feature(token, v['heading_deg'])
            cat = categories[category]
            if heading not in {v['heading_deg'] for v in r['views']}:
                raise ValueError('Feature refers to an unobserved heading')
            source = {'kind':'streetview_observation', 'review_id':r['id'], 'heading_deg':heading,
                      'image_date':v['image_date'], 'url':v['url'].split('&heading=')[0]+'&heading='+str(heading)}
            binding = next((b for b in bindings if b['category'] == category and r['id'] in b['review_ids']), None)
            if binding:
                if binding['osm_id'] not in mapped:
                    raise ValueError('Mapped landmark has no complete ground')
                mapped[binding['osm_id']]['source'].append(source)
                continue
            if category == 'building':
                # Nearby boxes provide context, not a claimed one-to-one visual identification.
                nearby = [o for o, dist in zip(buildings, np.linalg.norm(building_points-[px, pz], axis=1)) if dist < 90]
                for o in nearby:
                    if r['id'] not in o['context_reviews']:
                        o['context_reviews'].append(r['id'])
                aliases.append({'review_id':r['id'], 'feature':token,
                                'status':'nearby_OSM_context_not_individual_facade_identification',
                                'codes':[o['code'] for o in nearby]})
                continue
            code = observation_code(v['pano_id'], cat['code'], bearing)
            if code in by_code:
                by_code[code]['source'].append(source)
                continue
            angle = math.radians(bearing)
            obj = {'code':code, 'category':category, 'family':cat['family'],
                   'description':cat['label']+', '+side_names[side]+' nella vista: '+obs['description']+'.',
                   'sector':r['sector'], 'position_m':[px, 0, pz],
                   # Compass heading maps into +X east, +Z south; local X follows the road.
                   'yaw_deg':(90-heading) % 360,
                   'primitives':recipe(cat), 'source':[source],
                   'position_status':'estimated_visual_group_locator_not_metric_location',
                   'dimensions_status':'design_assumption', 'collision_enabled':False,
                   'side_in_view':side, 'bearing_deg':bearing,
                   'runtime_status':'deferred_no_safe_ground_placement',
                   'panorama_point_lon_lat':[v['longitude'], v['latitude']],
                   'scope':'representative_group_not_individual_count_or_continuous_extent'}
            for distance in np.arange(cat['offset_m'], cat['offset_m']+51, 2):
                x, z = px+math.sin(angle)*distance, pz-math.cos(angle)*distance
                obj['position_m'] = [float(x), 0, float(z)]
                shape = footprint(obj)
                if shape.intersects(protected) or shape.intersects(obstacle):
                    continue
                pts = list(shape.envelope.exterior.coords)+[(x, z)]
                hh = terrain_height(chunks, [p[0] for p in pts], [p[1] for p in pts])
                if not np.isfinite(hh).all():
                    continue
                # Vegetation group is grounded per primitive below, not suspended as one rigid mat.
                obj['position_m'][1] = float(hh[-1])
                obj['placement_distance_assumption_m'] = float(distance)
                obj['runtime_status'] = 'visible_blockout'
                for p in obj['primitives']:
                    cx, _, cz = p['center_m']
                    a = math.radians(obj['yaw_deg'])
                    wx, wz = x+cx*math.cos(a)+cz*math.sin(a), z-cx*math.sin(a)+cz*math.cos(a)
                    ground = float(terrain_height(chunks, wx, wz))
                    if not math.isfinite(ground):
                        raise ValueError('Missing primitive ground after bounding check')
                    p['center_m'][1] += ground-obj['position_m'][1]
                break
            if obj['runtime_status'] != 'visible_blockout':
                # Keep a finite panorama-based locator in the deferred inventory, never a fake Y=0.
                ground = float(terrain_height(chunks, px, pz))
                if not math.isfinite(ground):
                    raise ValueError('Missing terrain at observed panorama')
                obj['position_m'] = [px, ground, pz]
            by_code[code] = obj
            objects.append(obj)
    tiles = defaultdict(list)
    for o in objects:
        o['position_m'] = [round(float(v), 6) for v in o['position_m']]
        o['yaw_deg'] = round(float(o['yaw_deg']), 6)
        for p in o['primitives']:
            for k in ['size_m', 'center_m']:
                p[k] = [round(float(v), 6) for v in p[k]]
        e, n = o['position_m'][0]+origin[0], origin[1]-o['position_m'][2]
        lon, lat = inverse.transform(e, n)
        o['point_lon_lat'] = [round(lon, 8), round(lat, 8)]
        key = tuple(math.floor(o['position_m'][i]/128)*128 for i in [0, 2])
        o['tile_id'] = chunk_ids[key]
        if o['runtime_status'] == 'visible_blockout':
            shape = footprint(o)
            if shape.intersects(protected):
                raise ValueError('Placeholder intersects protected road: '+o['code'])
            o['road_clearance_m'] = round(float(shape.distance(road)), 6)
            tiles[o['tile_id']].append(o['code'])
        validate_object(o)
    inputs = [config_path, GEO/'streetview_views.csv', GEO/'streetview_observations.csv',
              GEO/'osm_circuit_environment.geojson', GEO/'osm_circuit_environment_provenance.json',
              GEO/'circuito_osm_candidate_20261020.geojson', Path(__file__), ROOT/'tools/coffa/environment.py']
    fingerprints = {str(p.relative_to(ROOT)).replace('\\', '/'):
                    hashlib.sha256(p.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in inputs}
    fingerprints['construction_manifest'] = sha(source_manifest)
    fingerprints['shoulders_manifest'] = sha(folder/'shoulders.json')
    coverage = {'review_count':len(reviews), 'view_count':sum(map(len, views.values())),
                'unique_panorama_count':len({v['pano_id'] for vs in views.values() for v in vs}),
                'route_length_horizontal_m':round(length, 3),
                'baseline_count':len(baseline_rows), 'baseline_target_spacing_m':250,
                'baseline_max_gap_m':round(max(b['station_m']-a['station_m'] for a, b in zip(baseline_rows, baseline_rows[1:])), 3),
                'all_sectors_have_observed_stations':set(r['sector'] for r in reviews) == set('ABCVDEF'),
                'max_panorama_offset_from_target_m':round(max_snap, 3),
                'continuous_visual_coverage_verified':False,
                'unseen_intervals':'Between stations, around occluded bends, behind buildings and vegetation; not certified as continuously viewed',
                'individual_objects_exhaustively_surveyed':False,
                'dates_are_mixed':True}
    result = {'schema_version':1, 'status':'coded_visual_environment_blockout_not_survey',
              'horizontal_crs':'EPSG:6708', 'axes':manifest['axes'], 'origin_ENH_m':origin,
              'construction_manifest_sha256':sha(source_manifest),
              'build_id':hashlib.sha256(encode(fingerprints)).hexdigest()[:20],
              'reviewed_date':'2026-10-21', 'coverage':coverage,
              'categories':categories, 'render_distance_m':config['render_distance_m'],
              'fingerprints':fingerprints, 'objects':sorted(objects, key=lambda o:o['code']),
              'tiles':dict(sorted(tiles.items())), 'reviews':reviews, 'building_context_links':aliases,
              'covered_legacy_osm_ids':sorted(existing & osm_ids),
              'deferred_source_buildings':deferred_sources,
              'landmark_bindings':bindings,
              'protected_road_and_shoulder_margin_m':margin,
              'original_rasters_modified':False, 'road_or_shoulders_modified':False,
              'google_imagery_copied':False,
              'dimensions_inferred_from_perspective':False}
    atomic_write(GEO/'circuit_placeholders.json', encode(result))
    atomic_write(ROOT/'reports/CATALOGO_SEGNAPOSTO.html', catalog_html(result))
    table = io.StringIO(newline='')
    writer = csv.writer(table, delimiter=';', lineterminator='\n')
    writer.writerow(['code', 'category', 'sector', 'description', 'position_status', 'dimensions_status',
                     'runtime_status', 'x_m', 'y_m', 'z_m', 'yaw_deg', 'source_url'])
    for o in result['objects']:
        writer.writerow([o[k] for k in ['code', 'category', 'sector', 'description', 'position_status',
                                        'dimensions_status', 'runtime_status']]+o['position_m']+[o['yaw_deg'], o['source'][0]['url']])
    atomic_write(ROOT/'reports/CATALOGO_SEGNAPOSTO.csv', table.getvalue().encode('utf-8'))
    summary = {'build_id':result['build_id'], 'catalog_sha256':sha(GEO/'circuit_placeholders.json'),
               'coverage':coverage, 'object_count':len(objects), 'runtime_count':sum(map(len, tiles.values())),
               'counts_by_category':dict(sorted(Counter(o['category'] for o in objects).items())),
               'counts_by_status':dict(sorted(Counter(o['runtime_status'] for o in objects).items())),
               'legacy_buildings_replaced_without_duplicates':len(result['covered_legacy_osm_ids']),
               'source_buildings_deferred':deferred_sources,
               'legacy_boxes_deferred_for_road_conflict':sum(o['runtime_status'] != 'visible_blockout' for o in objects if o.get('osm_id') in existing),
               'collision_enabled':False, 'metric_survey':False}
    atomic_write(ROOT/'reports/AMBIENTE_CIRCUITO_CATALOGO.json', encode(summary))
    print(json.dumps(summary, indent=2))
    return result


if __name__ == '__main__':
    build()
