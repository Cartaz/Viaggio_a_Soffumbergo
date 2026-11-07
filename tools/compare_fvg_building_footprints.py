"""Compare regional building footprints with OSM and native candidate asphalt.

Independent source geometry audit only. Neither official CTRN nor DBTsped
footprints prove current ground-level wall positions, and this script never
modifies source terrain, road, native collision meshes, or packages.
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

from audit_swept_building_clearance import (
    build_swept_envelopes, digest, load_json, load_telemetry
)
from fetch_fvg_building_footprints import LAYERS, NATIVE_CRS
from review_mont_joanes_clearance import (
    TARGETS, actual_asphalt_polygon, locate_geometry, svg_path
)
from road_surface import RoadSurface

ROOT = Path(__file__).resolve().parents[1]
RADIUS_M = 32.0
COLORS = {
    "OSM": "#ff7979",
    "DBS_EDIFICATO": "#62cfb0",
    "EDIFICATO_CTRN_ED1_067": "#e9bf67",
    "EDIFICATO_CTRN_ED2_067": "#ba9be4"
}


def to_unreal_shapes(geojson, origin):
    """WFS data is in EPSG:6708 E,N and need not be reprojected."""
    ids, polys = [], []
    for feature in geojson["features"]:
        shape = shapely.force_2d(shapely.from_geojson(json.dumps(feature["geometry"])))
        if shape.is_empty or not shape.is_valid:
            raise ValueError("Invalid official feature: " + str(feature.get("id")))
        shape = shapely.transform(
            shape, lambda p: np.c_[p[:, 0]-origin[0], origin[1]-p[:, 1]]
        )
        if shape.geom_type not in ("Polygon", "MultiPolygon"):
            raise ValueError("Unsupported official feature")
        ids.append(feature["id"])
        polys.append(shape)
    return ids, np.asarray(polys, dtype=object)


def compare_layer(target, feature_ids, shapes, asphalt, chassis, window):
    """Do not identify the wall from an IoU score: it is only a candidate."""
    if len(feature_ids) != len(shapes):
        raise ValueError("Mismatched polygon/ID counts")
    local = np.flatnonzero(shapely.intersects(shapes, window))
    nearby = shapes[local]
    union = shapely.union_all(nearby) if len(nearby) else shapely.GeometryCollection()
    overlap = shapely.area(shapely.intersection(shapes, target))
    matching = np.flatnonzero(overlap > 1e-8)
    aggregate = shapely.union_all(shapes[matching]) if len(matching) else shapely.GeometryCollection()
    iou = float(shapely.area(shapely.intersection(target, aggregate))
                / shapely.area(shapely.union(target, aggregate))) if len(matching) else 0.
    # Match only by explicit overlap; no arbitrary nearest-building assignment.
    individual_iou = np.asarray([
        float(shapely.area(shapely.intersection(target, g))
              / shapely.area(shapely.union(target, g))) for g in nearby
    ])
    best_local = int(np.argmax(individual_iou)) if len(individual_iou) else None
    best = int(local[best_local]) if best_local is not None and individual_iou[best_local] > 0 else None
    road_areas = shapely.area(shapely.intersection(nearby, asphalt))
    chassis_areas = shapely.area(shapely.intersection(nearby, chassis))
    return {
        "regional_features_in_snapshot": len(shapes),
        "regional_features_in_window": len(local),
        "regional_ids_overlapping_osm_target": [feature_ids[x] for x in matching],
        "union_iou_with_osm_target": iou,
        "candidate_best_match_id": feature_ids[best] if best is not None else None,
        "candidate_best_match_iou": float(individual_iou[best_local]) if best is not None else 0.,
        "regional_union_asphalt_overlap_m2": float(shapely.area(shapely.intersection(union, asphalt))),
        "regional_union_chassis_overlap_m2": float(shapely.area(shapely.intersection(union, chassis))),
        "regional_features_touching_asphalt": int(np.count_nonzero(road_areas > 1e-8)),
        "regional_features_touching_chassis": int(np.count_nonzero(chassis_areas > 1e-8)),
        "true_wall_assignment_verified": False
    }


def draw_overlay(case, osm, asphalt, chassis, region_shapes, panoramas):
    width, height = 840, 680
    cx, cy = case["peak_center_UE_xy_m"]
    scale = min(width, height) / (2 * RADIUS_M)
    def path(shape):
        return svg_path(shape, cx, cy, scale, width, height)
    output = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        f'<rect width="{width}" height="{height}" fill="#151b20"/>',
        f'<path d="{path(asphalt)}" fill="#666b72" stroke="#9fa6ad" stroke-width="1" fill-rule="evenodd"/>'
    ]
    for layer in LAYERS:
        for shape in region_shapes[layer]:
            if not shape.is_empty:
                output.append(f'<path d="{path(shape)}" fill="none" stroke="{COLORS[layer]}" '
                              'stroke-width="2.2" stroke-dasharray="6 4" fill-rule="evenodd"/>')
    output.append(f'<path d="{path(osm)}" fill="{COLORS["OSM"]}" fill-opacity=".12" '
                  'stroke="#ff7979" stroke-width="2.8" fill-rule="evenodd"/>')
    output.append(f'<path d="{path(chassis)}" fill="#77ccff" fill-opacity=".3" '
                  'stroke="#b9ebff" stroke-width="2" fill-rule="evenodd"/>')
    for item in panoramas:
        x, y = item["position_UE_xy_m"]
        x0, y0 = (x-cx)*scale+width/2, (y-cy)*scale+height/2
        output.append(f'<circle cx="{x0:.2f}" cy="{y0:.2f}" r="5" fill="#ff8e5c" stroke="#222" stroke-width="1"/>')
    output += [
        f'<path d="M24,{height-31} h{10*scale:.1f}" stroke="white" stroke-width="3"/>',
        f'<text x="24" y="{height-43}" font-size="14" fill="white">10 m</text>',
        '<path d="M805,40 v-24 m-6,8 l6,-8 l6,8" stroke="white" stroke-width="2" fill="none"/>',
        '<text x="798" y="57" font-size="14" fill="white">N</text>',
        f'<text x="165" y="{height-18}" fill="#d2d9de" font-size="12">'
        'FVG EDIFICI · OSM contributors · fonte QA, non rilievo dei muri</text>',
        '</svg>'
    ]
    return "".join(output)


def build_html(cases, figures):
    items = []
    for c, fig in zip(cases, figures):
        rows = "".join(
            f'<tr><td>{html.escape(layer)}</td><td>{stats["regional_union_asphalt_overlap_m2"]:.3f} m²</td>'
            f'<td>{stats["regional_union_chassis_overlap_m2"]:.4f} m²</td>'
            f'<td>{stats["union_iou_with_osm_target"]:.3f}</td></tr>'
            for layer, stats in c["regional_comparisons"].items()
        )
        items.append(
            "<section><h2>" + html.escape(c["osm_id"]) + "</h2><div class='pair'><div>"
            + fig + "</div><div><p>OSM / asfalto: " + f'{c["osm_vs_asphalt_m2"]:.3f} m²'
            + "<br>OSM / telaio: " + f'{c["osm_vs_chassis_m2"]:.4f} m²'
            + "</p><table><tr><th>Fonte</th><th>Asfalto</th><th>Telaio</th><th>IoU OSM</th></tr>"
            + rows + "</table><p>Le impronte regionali non sono state identificate "
            "come muri a terra. Confronto geometrico planimetrico della sola candidata "
            "f437, non collaudo del pacchetto Unreal attivo.</p></div></div></section>"
        )
    return (
        '<!doctype html><html lang="it"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Mont Joanes | FVG EDIFICI e Unreal</title>'
        '<style>body{font:15px/1.6 system-ui,sans-serif;max-width:1340px;margin:auto;padding:22px;'
        'background:#141a20;color:#e8ebef}section{padding:18px;margin:24px 0;background:#222b34;'
        'border-radius:14px}.pair{display:grid;grid-template-columns:1.65fr 1fr;gap:20px}'
        'svg{width:100%}table{font-size:13px;border-collapse:collapse}td,th{text-align:left;'
        'padding:7px;border-bottom:1px solid #46515c}'
        '@media(max-width:850px){.pair{grid-template-columns:1fr}}</style></head><body>'
        '<h1>Via Mont Joanes, Canal di Grivò</h1>'
        '<p>Confronto fra impronte OSM, tre livelli regionali EDIFICI e il solo asfalto '
        'generato nella candidata Unreal f437. Le fonti rappresentano anni e metodi diversi.</p>'
        '<p><span style="color:#ff7979">OSM</span> · '
        '<span style="color:#62cfb0">DBTsped da Trueortofoto 2017–2020</span> · '
        '<span style="color:#e9bf67">CTRN edizione 1</span> · '
        '<span style="color:#ba9be4">CTRN edizione 2</span> · '
        'grigio: asfalto · azzurro: Yaris · arancione: panoramiche storiche</p>'
        + "".join(items)
        + '<p>Regione Autonoma Friuli Venezia Giulia, servizio EDIFICI WFS. '
        '© OpenStreetMap contributors, ODbL. Esiti di comparazione, non '
        'una certificazione di collisione né correzioni degli edifici.</p></body></html>'
    )


def analyze(snapshot: Path, prior_path: Path, output: Path):
    if output.exists():
        raise FileExistsError("Do not replace earlier geometry audit")
    manifest_path = snapshot / "manifest.json"
    source = load_json(manifest_path)
    if source["native_crs"] != NATIVE_CRS or source["status"] != "complete":
        raise ValueError("Invalid regional provenance")
    original = load_json(prior_path)
    if original["build_id"] != "f4373a62b482" or not original["all_source_data_unchanged"]:
        raise ValueError("Unverified local source report")
    # Verify original dependency fingerprints before touching candidate data.
    hashes = {}
    for row in original["protected_sources"]:
        file = Path(row["path"])
        if digest(file) != row["sha256"]:
            raise ValueError("Protected native file changed " + str(file))
        hashes[str(file)] = row["sha256"]
    official = {}
    for name in LAYERS:
        meta = source["layers"][name]
        path = snapshot / meta["filename"]
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
            raise ValueError("WFS snapshot fingerprint mismatch")
        data = json.loads(raw)
        if not data.get("crs", {}).get("properties", {}).get("name", "").endswith("::6708"):
            raise ValueError("Regional WFS CRS unexpectedly changed")
        if len(data["features"]) != meta["features"]:
            raise ValueError("Regional layer count changed")
        official[name] = data
        hashes[str(path)] = meta["sha256"]
    project_draft = ROOT / "results/road_drafts/f4373a62b482"
    import_report = load_json(project_draft / "import_report.json")
    native_manifest = load_json(Path(import_report["manifest"]))
    origin = np.asarray(native_manifest["origin_ENH_m"])
    official_shapes = {name: to_unreal_shapes(official[name], origin) for name in LAYERS}
    from pyproj import Transformer, network
    network.set_network_enabled(False)
    reproject = Transformer.from_crs(4326, 6708, always_xy=True, allow_ballpark=False)
    raw_osm = load_json(ROOT / "data/geography/world_cover_20261024_buildings_v4/cover.geojson")
    osm_features = {row["id"]: row for row in raw_osm["features"] if row["id"] in TARGETS}
    if set(osm_features) != set(TARGETS):
        raise ValueError("Target OSM polygon missing")
    osm = {key: locate_geometry(row, reproject, origin) for key, row in osm_features.items()}
    previous_sweep = load_json(ROOT / "results/building_context/f437_swept_chassis_20261106_v1/report.json")
    sampled = load_json(Path(previous_sweep["parent_sampled_report"]))
    lap = Path(sampled["native_full_lap_report"])
    telemetry = lap.parent / (lap.parent.name + ".csv")
    times, centers, quats = load_telemetry(telemetry)
    if len(times) != previous_sweep["pose_samples"]:
        raise ValueError("Not the original native telemetry")
    road = RoadSurface(native_manifest, include_shoulders=False)
    old_cases = {c["source_id"]: c for c in original["cases"]}
    cases, figures = [], []
    for fid in TARGETS:
        prev = old_cases[fid]
        xy = np.asarray(prev["peak_center_UE_xy_m"])
        window = shapely.box(xy[0]-RADIUS_M, xy[1]-RADIUS_M,
                             xy[0]+RADIUS_M, xy[1]+RADIUS_M)
        asphalt = actual_asphalt_polygon(road, window)
        if asphalt.is_empty:
            raise ValueError("Missing asphalt from native candidate")
        first, last = prev["peak_interval_time_s"]
        index = int(np.searchsorted(times, first))
        if abs(times[index]-first) > .002 or abs(times[index+1]-last) > .002:
            raise ValueError("Pose interpolation window changed")
        hulls, margin, valid, *_ = build_swept_envelopes(
            centers[index:index+2], quats[index:index+2], times[index:index+2])
        if not valid[0]:
            raise ValueError("Cannot interpolate a missing native frame")
        chassis = shapely.buffer(hulls[0], float(margin[0])+1e-7, quad_segs=8)
        area = float(shapely.area(shapely.intersection(chassis, osm[fid])))
        if abs(area-prev["swept_chassis_plan_overlap_m2"]) > 2e-5:
            raise ValueError("Earlier native chassis overlap not reproduced")
        comparisons = {}
        visual_layers = {}
        for name in LAYERS:
            ids, shapes = official_shapes[name]
            comparisons[name] = compare_layer(osm[fid], ids, shapes, asphalt, chassis, window)
            visual_layers[name] = [g.intersection(window) for g in shapes if g.intersects(window)]
        case = {
            "osm_id": fid,
            "peak_center_UE_xy_m": xy.tolist(),
            "osm_vs_asphalt_m2": float(shapely.area(shapely.intersection(osm[fid], asphalt))),
            "osm_vs_chassis_m2": area,
            "regional_comparisons": comparisons,
            "source_backed_wall_alignment_confirmed": False,
            "corrected_native_road_or_building_generated": False,
            "next_step": "Reconcile two epochs of map geometry with known street-level walls before changing game mesh"
        }
        cases.append(case)
        figures.append(draw_overlay(case, osm[fid], asphalt, chassis,
                                    visual_layers, original["panoramas"]))
    if not all(digest(Path(path)) == checksum for path, checksum in hashes.items()):
        raise ValueError("Source unexpectedly modified during audit")
    report = {
        "completed": True,
        "native_candidate_build_id": "f4373a62b482",
        "created_unix": time.time(),
        "fvg_source": source["service"],
        "fvg_snapshot_manifest_sha256": digest(manifest_path),
        "regional_crs": NATIVE_CRS,
        "regional_counts": {name: len(official[name]["features"]) for name in LAYERS},
        "native_window_size_m": [64, 64],
        "cases": cases,
        "protected_source_sha256": hashes,
        "no_native_assets_or_road_modified": True,
        "license_attribution": "Regione Autonoma Friuli Venezia Giulia, EDIFICI WFS; © OpenStreetMap contributors, ODbL 1.0",
        "limitations": "Independent map epochs, unverified ground-wall geometry; planar QA only, not source-verified game collision"
    }
    output.mkdir(parents=True)
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (output / "comparison.html").write_text(build_html(cases, figures), encoding="utf-8")
    for case, drawing in zip(cases, figures):
        (output / ("comparison_" + case["osm_id"].split("/")[-1] + ".svg")).write_text(drawing, encoding="utf-8")
    print(json.dumps({"output": str(output), "counts": report["regional_counts"], "cases": cases},
                     indent=2, ensure_ascii=False))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--prior-plan", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    analyze(args.snapshot.resolve(), args.prior_plan.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
