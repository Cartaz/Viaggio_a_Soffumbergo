#!/usr/bin/env python3
"""Extract the known, connected 2D return-branch sample from the cached OSM survey.

NOT a complete sector E, visual survey, motorable certification or road mesh.
Run: python tools/build_sector_e.py [--check]
"""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/geography/osm_survey.geojson"
PROVENANCE = ROOT / "data/geography/provenance.json"
OUTPUT = ROOT / "data/geography/sector_e_planimetry.geojson"
# OSM way topology: exit from Valle toward north, then west/south.
WAYS = (136494659, 136283440, 1041538032, 547054266)


def distance_2d(a, b):
    """Approximate local planimetric distance in metres (not 3D grade length)."""
    lat = math.radians((a[1] + b[1]) / 2.0)
    return math.hypot((b[0] - a[0]) * 111320.0 * math.cos(lat),
                      (b[1] - a[1]) * 111132.0)


def build(osm, provenance):
    if osm.get("type") != "FeatureCollection" or "features" not in osm:
        raise ValueError("Expected an OSM GeoJSON FeatureCollection")
    lookup = {f.get("properties", {}).get("osm_id"): f for f in osm["features"]}
    points, ranges = [], []
    travelled = 0.0
    for way_id in WAYS:
        way = lookup.get(way_id)
        if not way or way.get("geometry", {}).get("type") != "LineString":
            raise ValueError("Missing road way: " + str(way_id))
        props = way["properties"]
        if props.get("highway") not in ("residential", "unclassified"):
            raise ValueError("Way is not in the selected road class: " + str(way_id))
        if props.get("motor_vehicle") == "no":
            raise ValueError("Way explicitly disallows motor vehicles: " + str(way_id))
        coords = [list(p) for p in reversed(way["geometry"]["coordinates"])]
        if len(coords) < 2 or any(len(p) != 2 or not all(math.isfinite(v) for v in p)
                                  for p in coords):
            raise ValueError("Expected valid 2D coordinates: " + str(way_id))
        if points and distance_2d(points[-1], coords[0]) > 0.2:
            raise ValueError("Gap between consecutive OSM ways: " + str(way_id))
        section_len = sum(distance_2d(a, b) for a, b in zip(coords, coords[1:]))
        ranges.append({"osm_way_id": way_id, "highway": props["highway"],
                       "name": props.get("name"), "start_m": round(travelled, 1),
                       "end_m": round(travelled + section_len, 1)})
        travelled += section_len
        points.extend(coords[1:] if points else coords)
    return {
        "type": "FeatureCollection",
        "name": "Sector E — partial OSM planimetry, NOT the complete descent",
        "coordinate_reference": "WGS84 longitude, latitude (EPSG:4326); NO elevations",
        "attribution": "© OpenStreetMap contributors, ODbL 1.0",
        "features": [{
            "type": "Feature", "id": "E-PLAN-001",
            "properties": {
                "sector": "E",
                "status": "partial_planimetric_extract_unverified",
                "road_direction": "from Valle via Monte Piccat toward south (provisional)",
                "full_sector_boundary": "unknown_until_CIRCUITO_SOPRALLUOGO_is_available",
                "length_planimetric_m": round(travelled, 1),
                "measurement_method": "local_equirectangular_approximation",
                "osm_way_ranges": ranges,
                "source_file": "data/geography/osm_survey.geojson",
                "source_url": provenance["source"],
                "source_retrieved_utc": provenance["retrieved_utc"],
                "source_payload_sha256": provenance["source_payload_sha256"],
                "horizontal_datum": "WGS84",
                "vertical_datum": "not_available",
                "elevation_status": "unknown",
                "road_width_status": "unknown",
                "crossfall_status": "unknown",
                "surface_continuity_status": "not_verified",
                "visual_survey_coverage": "not_assessed",
                "drivability_status": "not_certified",
                "note": "Map geometry only. No Street View frames or copyrighted images included."
            },
            "geometry": {"type": "LineString", "coordinates": points}
        }]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail when derived data are stale")
    args = parser.parse_args()
    data = build(json.loads(SOURCE.read_text(encoding="utf-8")),
                 json.loads(PROVENANCE.read_text(encoding="utf-8")))
    if args.check:
        if not OUTPUT.exists() or json.loads(OUTPUT.read_text(encoding="utf-8")) != data:
            raise SystemExit("Sector E derived GeoJSON is missing or stale")
        print("Sector E planimetric extract matches OSM source (NOT visual/3D tested).")
    else:
        OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
        print("Wrote partial Sector E: %.1f m, %d nodes, no elevations." %
              (data["features"][0]["properties"]["length_planimetric_m"],
               len(data["features"][0]["geometry"]["coordinates"])))


if __name__ == "__main__":
    main()
