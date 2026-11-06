"""Build an evidence-only, locally rendered plan of Mont Joanes conflicts.

No new mesh or collision is generated. The figures represent OSM polygons,
the candidate's actual road triangles, recorded Yaris chassis and prior
panorama positions. These are different sources with different uncertainties.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from pathlib import Path
import time

import numpy as np
import shapely
from pyproj import Transformer, network

from audit_swept_building_clearance import (
    build_swept_envelopes, digest, load_json, load_telemetry, projected_chassis
)
from road_surface import RoadSurface

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ("way/36158227", "way/36158219")
VIEW_RADIUS_M = 32.0


def verify_input_hashes(report: dict) -> list[dict]:
    verified = []
    for path, expected in report["source_input_sha256"].items():
        file = Path(path)
        if not file.is_file() or digest(file) != expected:
            raise ValueError(f"Protected input absent or changed: {file}")
        verified.append({"path": str(file), "sha256": expected})
    return verified


def locate_geometry(feature, project, origin):
    geometry = shapely.from_geojson(json.dumps(feature["geometry"]))
    if geometry.geom_type == "LineString" and geometry.is_closed:
        geometry = shapely.Polygon(geometry.coords)
    geometry = shapely.transform(geometry, project.transform, interleaved=False)
    return shapely.transform(
        geometry, lambda p: np.c_[p[:, 0]-origin[0], origin[1]-p[:, 1]]
    )


def svg_path(shape, cx: float, cy: float, scale: float, width: int, height: int):
    def point(xy):
        return f"{(xy[0]-cx)*scale+width/2:.2f},{(xy[1]-cy)*scale+height/2:.2f}"
    def ring(coords):
        return "M" + " L".join(point(x) for x in coords) + " Z"
    if shape.is_empty:
        return ""
    if shape.geom_type == "Polygon":
        return " ".join([ring(shape.exterior.coords)] + [ring(r.coords) for r in shape.interiors])
    if shape.geom_type == "MultiPolygon":
        return " ".join(svg_path(g, cx, cy, scale, width, height) for g in shape.geoms)
    if shape.geom_type in ("LineString", "LinearRing"):
        return "M" + " L".join(point(x) for x in shape.coords)
    if shape.geom_type in ("MultiLineString", "GeometryCollection"):
        return " ".join(svg_path(g, cx, cy, scale, width, height) for g in shape.geoms)
    raise ValueError("Cannot render geometry type " + shape.geom_type)


def actual_asphalt_polygon(road: RoadSurface, box_m):
    """Extract *asphalt only* from the indexed native mesh triangles (cm -> m)."""
    bounds_cm = shapely.box(*(np.asarray(box_m.bounds)*100))
    indices = road.tree.query(bounds_cm, predicate="intersects")
    if not len(indices):
        return shapely.GeometryCollection()
    road_cm = shapely.union_all(road.polygons[indices]).intersection(bounds_cm)
    return shapely.transform(road_cm, lambda points: points/100)


def render_plan(case, road, route, chassis, swept, buildings, panorama, *,
                radius=VIEW_RADIUS_M):
    w, h = 920, 620
    scale = min(w, h) / (2*radius)
    cx, cy = case["center_UE_xy_m"]
    def path(geom):
        return svg_path(geom, cx, cy, scale, w, h)
    def xy(easting, northing):
        return ((easting-cx)*scale+w/2, (northing-cy)*scale+h/2)
    drawings = [
        f'<rect width="{w}" height="{h}" fill="#1e2328"/>',
        '<g stroke-linejoin="round" stroke-linecap="round">',
        f'<path d="{path(road)}" fill="#62666c" stroke="#92969c" stroke-width="1.2" fill-rule="evenodd"/>',
        f'<path d="{path(route)}" fill="none" stroke="#f4c765" stroke-width="2" stroke-dasharray="6 5"/>'
    ]
    for fid, polygon in buildings.items():
        important = fid == case["source_id"]
        fill, stroke = ("#b74f50", "#ff8b81") if important else ("#59615b", "#b5bcae")
        drawings.append(
            f'<path d="{path(polygon)}" fill="{fill}" fill-opacity=".6" '
            f'stroke="{stroke}" stroke-width="{2.4 if important else 1.1}" fill-rule="evenodd"/>'
        )
    drawings.append(
        f'<path d="{path(swept)}" fill="#76ddf1" fill-opacity=".23" '
        'stroke="#76ddf1" stroke-width="1.6" stroke-dasharray="3 3" fill-rule="evenodd"/>'
    )
    drawings.append(
        f'<path d="{path(chassis)}" fill="none" stroke="#f7f7f2" stroke-width="2.2"/>'
    )
    for pano in panorama:
        x, y = xy(*pano["position_UE_xy_m"])
        drawings.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5.2" fill="#f9a76a" stroke="#161a1e" stroke-width="1.3"/>')
        for heading in pano.get("headings_actually_seen", []):
            angle = np.radians(heading)
            vx, vy = float(np.sin(angle)), -float(np.cos(angle))
            drawings.append(
                f'<path d="M{x:.2f},{y:.2f} l{vx*17:.2f},{vy*17:.2f}" '
                'fill="none" stroke="#f9a76a" stroke-width="1.4"/>'
            )
    size = 10*scale
    drawings += [
        '</g>',
        f'<path d="M30,{h-35} h{size:.1f}" stroke="#fff" stroke-width="3"/>',
        f'<text x="30" y="{h-43}" fill="#fff" font-size="13">10 m · north up</text>',
        '<path d="M880,40 l0,-25 m-5,8 l5,-8 l5,8" fill="none" stroke="#fff" stroke-width="2"/>',
        '<text x="873" y="55" font-size="14" fill="#fff">N</text>',
        '<rect x="16" y="14" width="286" height="109" rx="8" fill="#13181c" fill-opacity=".88"/>',
        '<text x="27" y="34" font-size="13" fill="#ff8b81">ROSSO · impronta OSM target</text>',
        '<text x="27" y="51" font-size="13" fill="#bec5ca">GRIGIO · asfalto Unreal</text>',
        '<text x="27" y="68" font-size="13" fill="#f4c765">ORO · itinerario</text>',
        '<text x="27" y="85" font-size="13" fill="#76ddf1">AZZURRO · telaio interpolato</text>',
        '<text x="27" y="102" font-size="13" fill="#f9a76a">ARANCIONE · panorama registrato</text>',
        f'<text x="320" y="{h-20}" font-size="12" fill="#d2d4d6">'
        '© OpenStreetMap contributors (ODbL) · Unreal candidate f437 · non misurato</text>'
    ]
    return f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" aria-label="Planimetria ricostruita da fonti mappate e telemetria">' + "".join(drawings) + "</svg>"


def analyze(sweep_report: Path, visual_review: Path, out_dir: Path, *, radius=VIEW_RADIUS_M):
    if out_dir.exists():
        raise FileExistsError(f"Do not overwrite existing output: {out_dir}")
    report = load_json(sweep_report)
    if not report.get("diagnostic_completed") or not report.get("source_inputs_unchanged"):
        raise ValueError("Unverified sweep input")
    verified = verify_input_hashes(report)
    source_review = load_json(visual_review)
    if source_review["geometry_build_id"] != report["build_id"]:
        raise ValueError("Source review and telemetry refer to different builds")
    native_report = Path(report["parent_sampled_report"])
    if digest(native_report) != report["parent_sampled_report_sha256"]:
        raise ValueError("Sampled report hash does not match")
    draft = ROOT / "results/road_drafts" / report["build_id"]
    manifest = Path(load_json(draft / "import_report.json")["manifest"])
    m = load_json(manifest)
    if m["build_id"] != report["build_id"]:
        raise ValueError("Road manifest is from another build")
    origin = np.asarray(m["origin_ENH_m"], dtype=float)
    network.set_network_enabled(False)
    project = Transformer.from_crs(4326, 6708, always_xy=True, allow_ballpark=False)
    inverse = Transformer.from_crs(6708, 4326, always_xy=True, allow_ballpark=False)

    source_path = ROOT / "data/geography/world_cover_20261024_buildings_v4/cover.geojson"
    source = load_json(source_path)
    features = {f["id"]: f for f in source["features"] if f["id"] in TARGETS}
    if set(features) != set(TARGETS):
        raise ValueError("Missing one or more target footprints in original OSM extract")
    shapes = {fid: locate_geometry(f, project, origin) for fid, f in features.items()}
    if any(s.is_empty or not s.is_valid or s.geom_type not in ("Polygon", "MultiPolygon") for s in shapes.values()):
        raise ValueError("Missing or invalid mapped footprint")
    lap = Path(load_json(native_report)["native_full_lap_report"])
    telemetry = lap.parent / (lap.parent.name + ".csv")
    times, centers, orientations = load_telemetry(telemetry)
    if len(times) != report["pose_samples"]:
        raise ValueError("Telemetry length inconsistent")
    if not (np.isfinite(times).all() and np.isfinite(centers).all()):
        raise ValueError("Non-finite trajectory")
    index = {fid: c for c in report["cases"] for fid in [c["source_id"]]}
    route = shapely.LineString(np.asarray(load_json(draft/"circuit_itinerary.json")["points_cm"])[:, :2]/100)
    if not route.is_valid:
        raise ValueError("Invalid itinerary geometry")

    panorama = []
    for pose in source_review["poses"]:
        lat, lon = pose["displayed_wgs84"]
        e, n = project.transform(lon, lat)
        panorama.append({
            "displayed_wgs84": [lat, lon],
            "pano_id": pose["pano_id"],
            "displayed_location": pose["displayed_location"],
            "headings_actually_seen": pose["headings_actually_seen"],
            "observation": pose["observed"],
            "image_date": source_review["image_date"],
            "urls": pose["urls"],
            "position_UE_xy_m": [e-origin[0], origin[1]-n],
            "position_source": "Prior visually inspected panorama, not a surveyed camera position"
        })
    road = RoadSurface(m, include_shoulders=False)
    entries, rendered = [], []
    for fid in TARGETS:
        case = index[fid]
        lo, hi = case["peak_interval_s"]
        ix = int(np.searchsorted(times, lo, side="left"))
        if ix < 0 or ix+1 >= len(times) or abs(times[ix]-lo) > .002 or abs(times[ix+1]-hi) > .002:
            raise ValueError(f"Peak interval not found for {fid}")
        peak = (centers[ix, :2] + centers[ix+1, :2])/2
        view_box = shapely.box(peak[0]-radius,peak[1]-radius,peak[0]+radius,peak[1]+radius)
        # Local "drivable" helper includes shoulders; explicitly use only asphalt.
        asphalt = actual_asphalt_polygon(road, view_box)
        if asphalt.is_empty:
            raise ValueError(f"No actual generated road surface at {fid}")

        swept, pad, valid, gap, step, angle = build_swept_envelopes(
            centers[ix:ix+2], orientations[ix:ix+2], times[ix:ix+2])
        if not valid[0]:
            raise ValueError(f"Peak interval not valid for {fid}")
        padded = shapely.buffer(swept[0], float(pad[0])+1e-7, quad_segs=8)
        positions = projected_chassis(centers[ix:ix+2], orientations[ix:ix+2])
        chassis = shapely.union(positions[0], positions[1])
        local_path = route.intersection(view_box)
        polygon = shapes[fid]
        overlap = float(shapely.area(shapely.intersection(asphalt, polygon)))
        gap_road = float(shapely.distance(asphalt, polygon))
        overlap_swept = float(shapely.area(shapely.intersection(padded, polygon)))
        if abs(overlap_swept-case["maximum_interpolated_plan_overlap_m2"]) > 0.00002:
            raise ValueError("Reconstruction mismatches original swept diagnostic")
        e, n = peak[0]+origin[0], origin[1]-peak[1]
        lon, lat = inverse.transform(e, n)
        info = {
            "source_id": fid,
            "candidate_lat_lon": [lat, lon],
            "peak_interval_time_s": [lo, hi],
            "peak_center_UE_xy_m": peak.tolist(),
            "mapped_building_area_m2": float(polygon.area),
            "generated_asphalt_intersection_m2_local_clip": overlap,
            "building_to_generated_asphalt_distance_m": gap_road,
            "swept_chassis_plan_overlap_m2": overlap_swept,
            "max_unobserved_interpolation_angle_deg": float(angle[0]),
            "translation_m_between_poses": float(step[0]),
            "chassis_geometry_from_original_native_source": True,
            "streetview_facade_association_status": (
                source_review["footprint_association_status"] if
                fid == source_review["candidate_source_id"] else
                "No source-backed facade-to-polygon match documented for this ID"
            ),
            "ground_level_wall_confirmed_for_this_osm_way": (
                False  # The visual review confirms a wall in scene, not the exact way identity.
            ),
            "review_required": True,
            "metric_observation_verified": False,
            "new_geometry_created": False,
            "layer_inputs": {
                "mapped_way": "OSM 2026-10-24 archived footprint, not parcel boundary",
                "asphalt": "actual triangle mesh from f437 candidate; engineered geometry",
                "chassis": "sampled native vehicle pose; between-frame interpolation conditional",
                "panoramas": "recorded Street View positions and headings, not georectified"
            }
        }
        entries.append(info)
        graphic = render_plan(
            {"source_id": fid, "center_UE_xy_m": peak.tolist()},
            asphalt, local_path, chassis, padded, shapes, panorama, radius=radius
        )
        rendered.append({"source_id": fid, "image": graphic, "case": info})
    # OSM source remains local; only metadata and observed panorama links appear in HTML.
    panels = []
    for item in rendered:
        fid = item["source_id"]
        c = item["case"]
        panels.append(
            '<section><h2>' + html.escape(fid) + '</h2>'
            '<div class="two"><div class="map">' + item["image"] + '</div>'
            '<div class="metrics"><p><b>Massima sovrapposizione telaio / OSM:</b> '
            + f'{c["swept_chassis_plan_overlap_m2"]:.5f} m²</p>'
            '<p><b>Asfalto generato / impronta OSM (ritaglio locale):</b> '
            + f'{c["generated_asphalt_intersection_m2_local_clip"]:.3f} m²</p>'
            '<p><b>Distanza minima asfalto–OSM:</b> '
            + f'{c["building_to_generated_asphalt_distance_m"]:.3f} m</p>'
            '<p><b>Equivalenza facciata–impronta:</b> non verificata</p>'
            '<p><a href="https://www.openstreetmap.org/' + fid + '" target="_blank" rel="noopener">OpenStreetMap: impronta archiviata</a></p>'
            '<p>Non applicare automaticamente collisioni o modifiche alla strada.</p></div></div></section>'
        )
    views = "".join(
        '<li>' + html.escape(p["displayed_location"]) + ': '
        + " · ".join('<a target="_blank" rel="noopener" href="' + html.escape(url, quote=True)
                   + '">vista registrata ' + str(i+1) + '</a>'
                   for i, url in enumerate(p["urls"]))
        + '</li>' for p in panorama
    )
    legend = '<div class="legend"><span style="color:#b74f50">■ Edificio target</span><span style="color:#62666c">■ Asfalto generato</span><span style="color:#f4c765">━ Itinerario</span><span style="color:#76ddf1">▧ Inviluppo Yaris</span><span style="color:#f9a76a">● Panorama</span></div>'
    page = ('<!doctype html><html lang="it"><meta charset="utf-8"><meta name="viewport" '
            'content="width=device-width, initial-scale=1"><title>Canal di Grivò · verifiche planimetriche</title>'
            '<style>body{font:16px/1.55 system-ui,Segoe UI,sans-serif;background:#131a20;color:#e5e7ec;max-width:1320px;margin:auto;padding:24px}'
            'section{background:#202a31;border:1px solid #35414b;border-radius:18px;margin:22px 0;padding:20px}'
            'h1,h2{color:#fff}a{color:#f9a76a}.two{display:grid;grid-template-columns: minmax(0,2fr) minmax(260px,1fr);gap:22px}'
            'svg{display:block;width:100%;border-radius:12px}.metrics{font-size:14px}.legend{display:flex;gap:18px;flex-wrap:wrap}'
            '.notice{color:#c2cbd1;font-size:14px}@media(max-width:870px){.two{grid-template-columns:1fr}}</style>'
            '<h1>Canal di Grivò · Via Mont Joanes</h1><p>Confronto planimetrico fra dati OSM del 24 ottobre 2026, '
            'asfalto effettivamente generato nella candidata f4373a62b482 e telemetria nativa.'
            ' La panoramica è un punto di osservazione, non un allineamento metrico.</p>'
            + legend + "".join(panels)
            + '<section><h2>Riferimenti visivi registrati</h2><ul>' + views + '</ul>'
            '<p>Rilievo storico: muratura in pietra al piano stradale con margine pavimentato rialzato; '
            'gronde e sovrastrutture sono distinte. La corrispondenza muro/way non è stata misurata.</p></section>'
            '<p class="notice">Nessuna collisione 3D è stata dimostrata. Impronte OSM, quote LiDAR, '
            'traslazioni e panorami hanno precisioni differenti. Non si ridistribuiscono fotografie.</p></html>')
    output = {
        "version": 1,
        "build_id": report["build_id"],
        "created_unix": time.time(),
        "source_sweep_sha256": digest(sweep_report),
        "source_visual_review_sha256": digest(visual_review),
        "protected_sources": verified,
        "local_map_radius_m": radius,
        "cases": entries,
        "panoramas": panorama,
        "reconstruction_no_mesh_or_asset_change": True,
        "real_collision_proven": False,
        "all_source_data_unchanged": all(
            digest(Path(f["path"])) == f["sha256"] for f in verified
        ),
        "source": "OSM © OpenStreetMap contributors (ODbL 1.0) and local native Unreal telemetry",
        "limits": "Visual comparison only; not measured building facade, 3D collision, roof or car upper accessories."
    }
    if not output["all_source_data_unchanged"]:
        raise ValueError("Source data changed during reading")
    out_dir.mkdir(parents=True)
    (out_dir/"review.json").write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir/"review.html").write_text(page, encoding="utf-8")
    for item in rendered:
        name = "plan_" + item["source_id"].split("/")[-1] + ".svg"
        (out_dir/name).write_text(item["image"], encoding="utf-8")
    print(json.dumps({
        "build_id": output["build_id"], "cases": entries,
        "source_data_unchanged": output["all_source_data_unchanged"],
        "output": str(out_dir)
    }, indent=2, ensure_ascii=False))
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--swept-report", type=Path, default=ROOT/"results/building_context/f437_swept_chassis_20261106_v1/report.json")
    p.add_argument("--visual-review", type=Path, default=ROOT/"results/territory/canal_mont_joanes_building_clearance_review_20261025.json")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--radius-m", type=float, default=VIEW_RADIUS_M)
    a = p.parse_args()
    if not np.isfinite(a.radius_m) or not 15 <= a.radius_m <= 200:
        p.error("Map radius should be 15–200 m")
    analyze(a.swept_report.resolve(), a.visual_review.resolve(), a.output.resolve(), radius=a.radius_m)


if __name__ == "__main__":
    main()
