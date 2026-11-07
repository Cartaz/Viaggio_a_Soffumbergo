"""Create public, attributed source-comparison maps from locally verified data.

No source GeoJSON or telemetry is uploaded. SVG portrays the *mapped* source
footprints, not measured current ground-wall positions or native collisions.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import shapely

from audit_swept_building_clearance import digest, load_json
from compare_fvg_building_footprints import COLORS, to_unreal_shapes
from fetch_fvg_building_footprints import LAYERS
from review_mont_joanes_clearance import TARGETS, actual_asphalt_polygon, locate_geometry, svg_path
from road_surface import RoadSurface

ROOT = Path(__file__).resolve().parents[1]


def render_overview(asphalt, route, osm, fvg, hotspots, *, center, radius):
    w, h = 900, 900
    scale = min(w,h)/(2*radius)
    cx, cy = center
    def path(geom):
        return svg_path(geom,cx,cy,scale,w,h)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 900" '
        'aria-label="FVG edifici, sorgenti OSM e cinque possibili interferenze Yaris">',
        '<rect width="900" height="900" fill="#111b22"/>',
        f'<path d="{path(asphalt)}" fill="#5f6670" stroke="#9da7b2" stroke-width="1.2" fill-rule="evenodd"/>',
        f'<path d="{path(route)}" fill="none" stroke="#eff4f6" stroke-width="1.6" stroke-dasharray="5 5"/>'
    ]
    for name in LAYERS:
        for polygon in fvg[name]:
            if polygon.is_empty:
                continue
            parts.append(f'<path d="{path(polygon)}" fill="none" stroke="{COLORS[name]}" '
                         'stroke-width="1.7" stroke-dasharray="5 3" fill-rule="evenodd"/>')
    for fid, polygon in osm.items():
        parts.append(f'<path d="{path(polygon)}" fill="#ff7979" fill-opacity=".10" '
                     'stroke="#ff7979" stroke-width="2.4" fill-rule="evenodd"/>')
    for rank, hit in enumerate(hotspots, start=1):
        x, y = hit["ue_xy"]
        sx, sy = (x-cx)*scale+w/2, (y-cy)*scale+h/2
        parts.extend([
            f'<circle cx="{sx:.2f}" cy="{sy:.2f}" r="10.2" stroke="#121a20" stroke-width="2" fill="#ff9d57"/>',
            f'<text x="{sx:.2f}" y="{sy+4.3:.2f}" text-anchor="middle" font-weight="bold" font-size="12" fill="#161a1e">{rank}</text>'
        ])
    parts += [
        f'<path d="M35,{h-35} h{20*scale:.1f}" stroke="#fff" stroke-width="3"/>',
        f'<text x="35" y="{h-47}" font-size="14" fill="white">20 m</text>',
        '<path d="M850,46 v-28 m-7,9 l7,-9 l7,9" stroke="#fff" stroke-width="2" fill="none"/>',
        '<text x="843" y="62" font-size="14" fill="#fff">N</text>',
        '<rect x="15" y="15" width="317" height="125" rx="8" fill="#17222b" fill-opacity=".9"/>',
        '<text x="28" y="36" font-size="15" fill="#ff7979">Rosso: impronte OSM target</text>',
        '<text x="28" y="57" font-size="15" fill="#62cfb0">Verde: DBTsped FVG</text>',
        '<text x="28" y="78" font-size="15" fill="#e9bf67">Giallo: CTRN 1a ed.</text>',
        '<text x="28" y="99" font-size="15" fill="#ba9be4">Viola: CTRN 2a ed.</text>',
        '<text x="28" y="120" font-size="15" fill="#ff9d57">Arancio: hotspot Yaris / DBTsped</text>',
        '<text x="300" y="879" font-size="12" fill="#c4cbd1">'
        '© Regione FVG / © OpenStreetMap contributors · non è rilievo delle facciate</text>',
        '</svg>'
    ]
    return "".join(parts)


def generate(snapshot: Path, full_lap: Path, output: Path):
    if output.exists():
        raise FileExistsError("Preserve existing snapshot figures")
    source = load_json(snapshot/"manifest.json")
    runs = load_json(full_lap)
    if source["status"] != "complete" or not runs["complete"]:
        raise ValueError("Source inputs not completed")
    if digest(snapshot/"manifest.json") != runs["regional_snapshot_manifest_sha256"]:
        raise ValueError("Report refers to a different FVG snapshot")
    report = load_json(ROOT/"results/road_drafts/f4373a62b482/import_report.json")
    manifest = load_json(Path(report["manifest"]))
    origin = np.asarray(manifest["origin_ENH_m"], float)
    bb = source["native_bbox_e_n"]
    box = shapely.box(bb[0]-origin[0],origin[1]-bb[3],
                      bb[2]-origin[0],origin[1]-bb[1])
    center = (float((box.bounds[0]+box.bounds[2])/2),
              float((box.bounds[1]+box.bounds[3])/2))
    radius = source["radius_m"]
    regional = {}
    for name in LAYERS:
        details = source["layers"][name]
        file = snapshot / details["filename"]
        if hashlib.sha256(file.read_bytes()).hexdigest()!=details["sha256"]:
            raise ValueError("Archived WFS data changed")
        payload = load_json(file)
        _, polygons = to_unreal_shapes(payload, origin)
        regional[name] = [shape.intersection(box) for shape in polygons if shape.intersects(box)]
    from pyproj import Transformer, network
    network.set_network_enabled(False)
    project = Transformer.from_crs(4326, 6708, always_xy=True, allow_ballpark=False)
    raw_osm = load_json(ROOT/"data/geography/world_cover_20261024_buildings_v4/cover.geojson")
    osm = {f["id"]: locate_geometry(f, project, origin)
           for f in raw_osm["features"] if f["id"] in TARGETS}
    if set(osm)!=set(TARGETS):
        raise ValueError("Unmatched OSM sources")
    road = RoadSurface(manifest, include_shoulders=False)
    asphalt = actual_asphalt_polygon(road, box)
    draft = ROOT/"results/road_drafts/f4373a62b482/circuit_itinerary.json"
    route_points = np.asarray(load_json(draft)["points_cm"],float)[:,:2]/100
    route = shapely.LineString(route_points).intersection(box)
    candidates = runs["regional_layers"]["DBS_EDIFICATO"]["cases"][:5]
    points=[]
    for c in candidates:
        lat, lon = c["approx_peak_wgs84_lat_lon"]
        e,n=project.transform(lon,lat)
        points.append({
            "source_id": c["regional_id"],
            "peak_overlap_m2": c["max_interpolated_plan_overlap_m2"],
            "wgs84": [lat,lon],
            "ue_xy": [e-origin[0],origin[1]-n],
            "real_collision_confirmed": False
        })
    svg = render_overview(asphalt,route,osm,regional,points,center=center,radius=radius)
    ElementTree.fromstring(svg)
    rows="".join(
        '<tr><td>' + str(i) + '</td><td>' + html.escape(pt["source_id"]) + '</td><td>'
        + f'{pt["peak_overlap_m2"]:.3f} m²' + '</td><td>'
        + f'{pt["wgs84"][0]:.6f}, {pt["wgs84"][1]:.6f}</td></tr>'
        for i,pt in enumerate(points,1)
    )
    page=(
        '<!doctype html><html lang="it"><head><meta charset="utf-8">'
        '<title>Edifici FVG, Canal di Grivò</title>'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<style>body{font:15px/1.6 system-ui,sans-serif;max-width:1200px;margin:auto;padding:24px;background:#12191f;color:#eff2f4}'
        'main{display:grid;grid-template-columns:1.3fr 1fr;gap:25px}'
        'svg{width:100%}td,th{padding:7px;border-bottom:1px solid #3c4b55;text-align:left}'
        '@media(max-width:850px){main{grid-template-columns:1fr}}</style></head><body>'
        '<h1>Via Mont Joanes · le cinque criticità del DBTsped</h1>'
        '<p>240 × 240 m, confronto planimetrico di dati regionali FVG, OSM e strada '
        'della candidata Unreal f437. Nessun edificio o elemento stradale è stato '
        'modificato. I punti indicano sovrapposizioni 2D, non collisioni fisiche.</p>'
        '<main><div>' + svg + '</div><div><table><tr><th>N.</th><th>Identificativo FVG</th>'
        '<th>Area telaio</th><th>Lat, lon</th></tr>' + rows + '</table>'
        '<p>DBTsped da Trueortofoto 2017–2020; CTRN da edizioni cartografiche '
        'precedenti. Le differenze tra poligoni non giustificano la correzione '
        'automatica della facciata.</p><p>Il test non include altezza, tetto, '
        'albero, coffa o dati LiDAR DSM/DBM. Sono necessarie ulteriori '
        'verifiche visive e poi un collaudo nativo Unreal.</p></div></main>'
        '<p>Fonti: Regione Autonoma Friuli Venezia Giulia, servizio EDIFICI WFS; '
        '© OpenStreetMap contributors (ODbL). Rielaborazione illustrativa QA.</p>'
        '</body></html>'
    )
    output.mkdir(parents=True)
    (output/"overview.svg").write_text(svg,encoding="utf-8")
    (output/"overview.html").write_text(page,encoding="utf-8")
    (output/"hotspots.json").write_text(json.dumps(
        {"source_manifest_sha256": digest(snapshot/"manifest.json"),
         "full_lap_report_sha256": digest(full_lap), "top_5": points,
         "not_measured_walls": True}, indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"output":str(output),"hotspots":len(points),"svg_bytes":len(svg)}))
    return points


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot",type=Path,required=True)
    ap.add_argument("--full-lap",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    generate(a.snapshot.resolve(),a.full_lap.resolve(),a.output.resolve())


if __name__=="__main__":
    main()
