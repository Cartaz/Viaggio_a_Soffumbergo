#!/usr/bin/env python3
"""Explicit, cached OSM survey extract. Never fetches Google imagery/geometry.

python tools/fetch_geography.py --download
No network unless --download is supplied. One small query, no retry loop.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/geography"
QUERY = '''[out:json][timeout:45];
(
 way["highway"](46.120,13.325,46.180,13.415);
 way["building"](46.1550,13.3900,46.1590,13.3960);
 node["place"](46.120,13.325,46.180,13.415);
);
out body; >; out skel qt;
'''
ENDPOINT = "https://overpass-api.de/api/interpreter"
MAP_URL = "https://api.openstreetmap.org/api/0.6/map?bbox=13.3900,46.1550,13.3960,46.1590"


def from_xml(payload):
    """Normalize only geographic elements/tags; omit contributor personal metadata."""
    root = ET.fromstring(payload)
    elements = []
    for item in root:
        if item.tag not in ("node", "way"):
            continue
        e = {"type": item.tag, "id": int(item.attrib["id"])}
        tags = {t.attrib["k"]: t.attrib["v"] for t in item.findall("tag")}
        if tags:
            e["tags"] = tags
        if item.tag == "node":
            e.update(lat=float(item.attrib["lat"]), lon=float(item.attrib["lon"]))
        else:
            e["nodes"] = [int(n.attrib["ref"]) for n in item.findall("nd")]
        elements.append(e)
    return {"elements": elements}


def convert(data):
    nodes = {e["id"]: e for e in data["elements"] if e["type"] == "node" and "lat" in e}
    features = []
    for e in data["elements"]:
        tags = e.get("tags", {})
        if e["type"] == "way" and ("highway" in tags or "building" in tags):
            if not all(n in nodes for n in e["nodes"]):
                raise ValueError(f"Incomplete way {e['id']}")
            coords = [[nodes[n]["lon"], nodes[n]["lat"]] for n in e["nodes"]]
            polygon = "building" in tags and len(coords) >= 4 and coords[0] == coords[-1]
            geometry = {"type": "Polygon" if polygon else "LineString",
                        "coordinates": [coords] if polygon else coords}
        elif e["type"] == "node" and "place" in tags:
            geometry = {"type": "Point", "coordinates": [e["lon"], e["lat"]]}
        else:
            continue
        features.append({"type": "Feature", "id": f"{e['type']}/{e['id']}",
                         "properties": {"osm_type": e["type"], "osm_id": e["id"], **tags},
                         "geometry": geometry})
    return {"type": "FeatureCollection", "name": "Faedis_Valle_OSM_survey",
            "attribution": "© OpenStreetMap contributors, ODbL 1.0 — https://www.openstreetmap.org/copyright",
            "coordinate_reference": "WGS84 longitude, latitude; no elevations",
            "features": features}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--source", choices=("overpass", "editing-api"), default="overpass")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    raw_path = OUT / "osm_survey.raw.json"
    if args.download:
        source = ENDPOINT if args.source == "overpass" else MAP_URL
        post = urllib.parse.urlencode({"data": QUERY}).encode() if args.source == "overpass" else None
        req = urllib.request.Request(source, data=post,
                                     headers={"User-Agent": "Viaggio-a-Soffumbergo-research/0.1"})
        with urllib.request.urlopen(req, timeout=55) as response:
            payload = response.read(25_000_001)
        if len(payload) > 25_000_000:
            raise ValueError("Unexpectedly large response")
        data = json.loads(payload) if args.source == "overpass" else from_xml(payload)
        if "remark" in data:
            raise ValueError("Overpass returned a warning/error: " + data["remark"])
        convert(data)  # Validate before replacing cached data.
        # Cache normalized geometry, not XML contributor names/IDs/history.
        raw_path.write_text(json.dumps(data), encoding="utf-8")
        manifest = {"retrieved_utc": datetime.now(timezone.utc).isoformat(),
                    "source": source, "query": QUERY if args.source == "overpass" else None,
                    "source_payload_sha256": hashlib.sha256(payload).hexdigest(),
                    "osm_base_timestamp": data.get("osm3s", {}).get("timestamp_osm_base"),
                    "license": "ODbL-1.0", "copyright": "© OpenStreetMap contributors",
                    "scope": "regional road query" if args.source == "overpass" else "Valle village bounding box only",
                    "limitations": "Map extract only. No terrain, no surveyed heights, no certified drivable loop; building coverage may be incomplete. OSM ways may extend outside the requested box."}
        (OUT / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    result = convert(data)
    (OUT / "osm_survey.geojson").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Converted {len(result['features'])} mapped features; elevations absent.")


if __name__ == "__main__":
    main()
