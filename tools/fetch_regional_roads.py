#!/usr/bin/env python3
"""Acquire a regional 2D OSM road *network*, not a verified circuit.

Does not modify the small OSM survey of Valle kept in data/geography/.
No network activity without --download. Offline --input requires the ORIGINAL
Overpass JSON response with nodes and ways (not normalized GeoJSON).
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.parse
import urllib.request

try:
    from tools.fetch_geography import QUERY, ENDPOINT, convert
except ModuleNotFoundError:
    from fetch_geography import QUERY, ENDPOINT, convert

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "build/geodata/osm"
MAX_BYTES = 25_000_000


def _atomic_bytes(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".osm_regional_", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def normalize_regional(raw, source, digest, downloaded_utc=None):
    if not isinstance(raw, dict) or not isinstance(raw.get("elements"), list):
        raise ValueError("Expected Overpass JSON containing complete nodes and ways")
    if raw.get("remark"):
        raise ValueError("Overpass error: " + str(raw["remark"]))
    data = convert(raw)
    features = []
    for feature in data["features"]:
        kind, props = feature["geometry"]["type"], feature["properties"]
        if kind != "LineString" or not props.get("highway"):
            continue
        hwy = props["highway"]
        possible = (hwy in {"secondary", "tertiary", "primary", "residential",
                            "unclassified", "service", "living_street", "track"} and
                    all(props.get(key) not in {"private", "no"} for key in
                        ("access", "motor_vehicle", "vehicle", "motorcar")))
        p = dict(props)
        p.update({"possible_motor_road_candidate": possible,
                  "route_membership_verified": False,
                  "road_drivability_verified": False,
                  "road_surface_height_status": "unknown",
                  "data_origin": "openstreetmap_network_only"})
        features.append({"type": "Feature", "id": feature["id"],
                         "geometry": feature["geometry"], "properties": p})
    if not features:
        raise ValueError("Regional OSM query has no road ways")
    geojson = {"type": "FeatureCollection",
               "name": "Soffumbergo_regional_OSM_roads_NOT_verified_route",
               "coordinate_reference": "EPSG:4326 longitude latitude 2D only",
               "license_notice": "© OpenStreetMap contributors, ODbL 1.0",
               "route_status": "network_candidates_no_complete_loop_asserted",
               "features": sorted(features, key=lambda f: f["id"])}
    meta = {"schema_version": 1, "source_url": source,
            "query": QUERY, "source_response_sha256": digest,
            "downloaded_utc": downloaded_utc,
            "osm_base_timestamp": raw.get("osm3s", {}).get("timestamp_osm_base"),
            "feature_count": len(features),
            "possible_motor_road_candidates": sum(f["properties"]["possible_motor_road_candidate"] for f in features),
            "road_surface_height_status": "absent",
            "route_verified": False, "streetview_continuous_coverage": False,
            "license": "ODbL-1.0",
            "not_covered": ["a continuous circuit", "turn restrictions", "road widths", "grades",
                            "physical viability of one-way and private roads",
                            "complete hairpin survey", "bridges/overhead obstacles"]}
    return geojson, meta


def acquire(raw_payload, out=DEFAULT_OUT, source="local_Overpass_response", downloaded_utc=None):
    if len(raw_payload) > MAX_BYTES:
        raise ValueError("Oversize OSM response")
    raw = json.loads(raw_payload)
    geojson, metadata = normalize_regional(raw, source,
                                           hashlib.sha256(raw_payload).hexdigest(),
                                           downloaded_utc)
    output = Path(out)
    # All data validated before anything can be written.
    _atomic_bytes(output / "regional_roads.geojson",
                  (json.dumps(geojson, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    _atomic_bytes(output / "regional_roads_provenance.json",
                  (json.dumps(metadata, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return metadata


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    operation = ap.add_mutually_exclusive_group(required=True)
    operation.add_argument("--download", action="store_true", help="Explicit opt-in: query live Overpass")
    operation.add_argument("--input", type=Path, help="Replay saved original Overpass JSON response")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if args.download:
        request = urllib.request.Request(
            ENDPOINT, data=urllib.parse.urlencode({"data": QUERY}).encode("utf-8"),
            headers={"User-Agent": "Viaggio-a-Soffumbergo-GIS-research/0.2 (OSM ODbL)"})
        with urllib.request.urlopen(request, timeout=65) as response:
            payload = response.read(MAX_BYTES + 1)
        source = ENDPOINT
        acquired = datetime.now(timezone.utc).isoformat()
    else:
        payload = args.input.read_bytes()
        source = str(args.input.resolve())
        acquired = None
    metadata = acquire(payload, args.output, source, acquired)
    print(f"OSM: {metadata['feature_count']} road ways; "
          f"{metadata['possible_motor_road_candidates']} preliminary motor-road candidates.")
    print("Not a traced circuit. No terrain height, driving rights or turns verified.")


if __name__ == "__main__":
    main()
