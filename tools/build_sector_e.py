#!/usr/bin/env python3
"""Extract sector E panorama anchors from user's source document; no road geometry."""
import argparse
import json
import math
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/CIRCUITO_SOPRALLUOGO.md"
OUTPUT = ROOT / "data/geography/sector_e_anchors.geojson"
PATTERN = re.compile(
    r"^\| \[(CIR-1[234])\]\((https://www\.google\.com/maps/[^)]+)\)"
    r" \| (1[678]) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$",
    re.MULTILINE
)
EXPECTED = {"CIR-12": 16, "CIR-13": 17, "CIR-14": 18}


def build(text):
    features, seen = [], set()
    for match in PATTERN.finditer(text):
        ident, url, step, label, note, limitation = match.groups()
        if ident in seen or int(step) != EXPECTED[ident]:
            raise ValueError("Duplicate or incorrect panorama route step")
        seen.add(ident)
        query = parse_qs(urlsplit(url).query)
        lat, lon = (float(v) for v in query["viewpoint"][0].split(","))
        heading = float(query["heading"][0])
        date = re.search(r"\b20\d{2}-(?:0[1-9]|1[0-2])\b", label)
        if (not date or not all(math.isfinite(v) for v in (lat, lon, heading))
                or not -90 <= lat <= 90 or not -180 <= lon <= 180
                or not 0 <= heading < 360):
            raise ValueError("Invalid panorama date/coordinates")
        features.append({
            "type": "Feature",
            "id": ident,
            "properties": {
                "sector": "E",
                "route_step": int(step),
                "imagery_date": date.group(0),
                "place": label.replace(" · " + date.group(0), ""),
                "heading_deg": heading,
                "observation": note.strip(),
                "limitation": limitation.strip(),
                "evidence": "source_report_2026_10_19_not_reobserved",
                "coverage": "isolated_panorama_only",
                "source_url": url
            },
            "geometry": {"type": "Point", "coordinates": [lon, lat]}
        })
    if seen != set(EXPECTED):
        raise ValueError("Missing one of CIR-12 / CIR-13 / CIR-14")
    features.sort(key=lambda f: f["properties"]["route_step"])
    return {
        "type": "FeatureCollection",
        "name": "Sector E, Costalunga and Mont Joanes: three isolated panorama anchors",
        "coordinate_reference": "EPSG:4326 lon/lat panorama viewpoint (no elevation)",
        "source_document": "docs/CIRCUITO_SOPRALLUOGO.md",
        "road_geometry_available": False,
        "continuous_survey_completed": False,
        "terrain_elevation_available": False,
        "features": features
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = json.dumps(build(INPUT.read_text(encoding="utf-8")),
                          ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != expected:
            raise SystemExit("Sector E anchors are missing or stale")
        print("Sector E anchors match source (road survey NOT complete).")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(expected, encoding="utf-8")
        print("Created three panorama anchors; no drivable polyline.")


if __name__ == "__main__":
    main()
