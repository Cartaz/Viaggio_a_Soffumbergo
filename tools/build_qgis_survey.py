#!/usr/bin/env python3
"""Prepare honest 2D QGIS GeoJSON layers from existing Soffumbergo evidence.

No download, Google geometry tracing, vertical data, interpolated missing
sectors, or claim that an OSM way is drivable. Python stdlib only.
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    ("data/geography/sector_a_observations.geojson", "A"),
    ("data/geography/sector_b_observations.geojson", "B"),
    ("data/geography/sector_c_partial.geojson", "C"),
    ("data/geography/sector_v_route.geojson", "V"),
    ("data/geography/sector_e_anchors.geojson", "E"),
    ("data/geography/settore_f_ancore.geojson", "F"),
    ("data/geography/survey_points.geojson", "VALLE"),
    ("data/geography/osm_survey.geojson", "VALLE_OSM_CONTEXT"),
)
SECTORS = ("A", "B", "C", "V", "D", "E", "F")
ROAD_INPUTS = {"data/geography/sector_c_partial.geojson", "data/geography/sector_v_route.geojson"}


def _coordinates(geometry):
    kind = geometry.get("type")
    raw = geometry.get("coordinates")
    if kind == "Point":
        positions = [raw]
    elif kind == "LineString":
        positions = raw
    elif kind == "Polygon":
        positions = [pt for ring in raw for pt in ring]
    else:
        raise ValueError("Unsupported GeoJSON geometry: " + str(kind))
    if not positions or any(not isinstance(pt, list) or len(pt) != 2 or
                            any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in pt) or
                            not (-180 <= pt[0] <= 180 and -90 <= pt[1] <= 90)
                            for pt in positions):
        raise ValueError("Coordinates must be finite WGS84 [longitude, latitude], with NO height")
    if kind == "LineString" and len(positions) < 2:
        raise ValueError("Short LineString")
    if kind == "Polygon" and any(len(ring) < 4 or ring[0] != ring[-1] for ring in raw):
        raise ValueError("Open/short polygon ring")
    return positions


def _feature(original, source, sector):
    geometry = original["geometry"]
    _coordinates(geometry)
    p = original.get("properties") or {}
    fid = str(original.get("id") or p.get("id") or p.get("osm_id") or "unlabelled")
    kind = geometry["type"]
    evidence = ("osm_2d_context" if source.endswith("osm_survey.geojson") else
                "osm_2d_partial_line" if kind == "LineString" else
                "reference_viewpoint_or_itinerary_anchor")
    return {"type": "Feature", "id": source + ":" + fid,
            "properties": {
                "ref_id": fid,
                "sector": sector,
                "name": str(p.get("name") or p.get("place") or fid),
                "origin_file": source,
                "source_url": str(p.get("source_url") or p.get("url") or ""),
                "evidence_role": evidence,
                "height_status": "NOT_AVAILABLE",
                "metric_status": "PLANIMETRY_ONLY_NOT_SURVEYED",
                "original_status": str(p.get("status") or p.get("coverage") or "not_specified"),
            }, "geometry": geometry}


def _geojson(features, name):
    return {"type": "FeatureCollection", "name": name,
            "coordinate_reference": "WGS84 / EPSG:4326; 2D only",
            "status": "not_a_continuous_road_and_not_a_terrain_model",
            "features": features}


def build(root=ROOT, output=None):
    root = Path(root)
    out = Path(output) if output is not None else root / "build/qgis"
    points, reference_lines, context_roads, buildings = [], [], [], []
    for relative, sector in SOURCES:
        src = root / relative
        source_data = json.loads(src.read_text(encoding="utf-8"))
        if source_data.get("type") != "FeatureCollection":
            raise ValueError(f"Not a FeatureCollection: {relative}")
        for original in source_data["features"]:
            kind = original["geometry"]["type"]
            obj = _feature(original, relative, sector)
            if kind == "Point":
                points.append(obj)
            elif kind == "LineString":
                if relative in ROAD_INPUTS:
                    reference_lines.append(obj)
                elif relative.endswith("osm_survey.geojson"):
                    context_roads.append(obj)
                else:
                    raise ValueError(f"Unexpected line geometry: {relative}")
            elif kind == "Polygon":
                if not relative.endswith("osm_survey.geojson"):
                    raise ValueError(f"Unexpected footprint: {relative}")
                buildings.append(obj)
    # Sector D has only boundary references; NEVER fabricate a connector LineString.
    # The actual V->D handoff is the first vertex of the mapped V outbound OSM
    # line, not the position of the nearby Street View panorama CIR-VAL-15.
    outbound = next((f for f in reference_lines
                     if f["properties"]["ref_id"] == "V-OUTBOUND"), None)
    byid = {f["properties"]["ref_id"]: f for f in points}
    if outbound is None or "CIR-12" not in byid:
        raise ValueError("Sector D requires OSM V-OUTBOUND start and E panorama CIR-12")
    start = json.loads(json.dumps(outbound))
    start["id"] = "boundary:D-START"
    start["geometry"] = {"type": "Point", "coordinates": outbound["geometry"]["coordinates"][0]}
    start["properties"].update({"ref_id": "D-START", "sector": "D",
                                "name": "Settore D: ingresso dal nodo OSM del settore V",
                                "evidence_role": "sector_boundary_osm_2d_not_survey_control"})
    end = json.loads(json.dumps(byid["CIR-12"]))
    end["id"] = "boundary:D-END"
    end["properties"].update({"ref_id": "D-END", "sector": "D",
                              "name": "Settore D: uscita approssimata dal panorama CIR-12",
                              "evidence_role": "sector_boundary_viewpoint_not_survey_control"})
    points.extend([start, end])
    layers = {
        "observation_anchors.geojson": points,
        "road_centerlines_partial.geojson": reference_lines,
        "valle_context_roads.geojson": context_roads,
        "valle_footprints.geojson": buildings,
    }
    out.mkdir(parents=True, exist_ok=True)
    for filename, features in layers.items():
        (out / filename).write_text(json.dumps(_geojson(features, filename), ensure_ascii=False,
                                               indent=2) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "status": "QGIS_2D_STAGING_ONLY_DTM_NOT_DOWNLOADED",
        "input_sources": [source for source, _ in SOURCES],
        "horizontal_crs": "EPSG:4326 input; use RDN2008 / UTM 33N EPSG:7792 (E,N) for GIS measurement; regional DTM may report EPSG:6708 (N,E)",
        "vertical_datum": None,
        "height_samples": 0,
        "continuous_loop_centerline": False,
        "layer_feature_counts": {name: len(features) for name, features in layers.items()},
        "sector_D": "Only approximate boundary references. No road line in repository.",
        "quality_warning": "OSM lines 2D only; Street View points for visual reference only; no length/radius/slope/width or drivable route certified.",
        "rights": "OSM derived geometry © OpenStreetMap contributors, ODbL 1.0; Google links and textual notes only; no imagery redistributed.",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = build(args.root, args.output)
    print(json.dumps(result["layer_feature_counts"], ensure_ascii=False))
    print("2D QGIS staging only: not a finished loop and not a terrain model")


if __name__ == "__main__":
    main()
