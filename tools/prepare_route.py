#!/usr/bin/env python3
"""Convert a height-resolved GeoJSON LineString into Godot/Blender blockout data.

Never infer an elevated drivable route from a screenshot or heightless OSM way.
Usage: python tools/prepare_route.py surveyed.geojson out.json --width 5.0
Required feature properties: source_url, horizontal_datum=WGS84,
vertical_datum=WGS84_ellipsoid, elevation_status=verified. Transform orthometric
DTM heights externally with the appropriate geoid before calling this tool.
"""
import argparse
import json
import math
from pathlib import Path
from coffa.geography import resample, road_strip, to_godot


def prepare(feature, width, step):
    if feature.get("type") != "Feature" or feature.get("geometry", {}).get("type") != "LineString":
        raise ValueError("Expected one GeoJSON LineString feature")
    meta = feature.get("properties", {})
    required = {"horizontal_datum": "WGS84", "vertical_datum": "WGS84_ellipsoid",
                "elevation_status": "verified"}
    if any(meta.get(k) != v for k, v in required.items()) or not meta.get("source_url"):
        raise ValueError("Source, horizontal/vertical datum and verified elevation metadata required")
    coordinates = feature["geometry"]["coordinates"]
    if len(coordinates) < 2:
        raise ValueError("Empty/short route")
    origin = coordinates[0]
    points = resample([to_godot(c, origin) for c in coordinates], step)
    vertices, triangles = road_strip(points, width)
    return {"schema_version": 1, "status": "blockout_requires_surface_survey",
            "source": meta, "origin_wgs84": origin, "axes": "+X east, +Y up, +Z south",
            "width_m": width, "width_status": "operator_supplied_not_surveyed",
            "crossfall_status": "unknown_zero_for_blockout", "points_m": points,
            "length_m": sum(math.dist(a, b) for a, b in zip(points, points[1:])),
            "vertices_m": vertices, "triangles": triangles}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--width", type=float, required=True)
    p.add_argument("--step", type=float, default=3.0)
    args = p.parse_args()
    result = prepare(json.loads(args.input.read_text()), args.width, args.step)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Prepared {result['length_m']:.1f} m; width/crossfall are provisional.")


if __name__ == "__main__":
    main()
