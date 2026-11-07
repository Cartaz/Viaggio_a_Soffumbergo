"""Acquire a small, provenance-preserving FVG building WFS comparison snapshot.

Only the regional EPSG:6708 BBOX is supported, never send WGS84 degrees as an
unqualified native WFS BBOX. This tool does not import or alter game buildings.
The raw extracts stay under results/, which is ignored in the public repo.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

from pyproj import Transformer
import shapely

ROOT = Path(__file__).resolve().parents[1]
WFS = "https://serviziogc.regione.fvg.it/geoserver/EDIFICI/ows"
LAYERS = (
    "DBS_EDIFICATO",
    "EDIFICATO_CTRN_ED1_067",
    "EDIFICATO_CTRN_ED2_067",
)
NATIVE_CRS = "EPSG:6708"
CENTER_WGS84 = (13.3607, 46.16735)
DEFAULT_RADIUS_M = 120.0
MAX_FEATURES = 1000
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


def query_parameters(name: str, bounds: tuple[float, float, float, float]):
    if name not in LAYERS or len(bounds) != 4 or bounds[0] >= bounds[2] or bounds[1] >= bounds[3]:
        raise ValueError("Unknown layer or invalid bounds")
    return {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": "EDIFICI:" + name,
        "bbox": ",".join(f"{v:.6f}" for v in bounds),
        "outputFormat": "application/json",
        "maxFeatures": str(MAX_FEATURES),
    }


def validate_snapshot(payload: bytes, layer: str, bounds):
    """Reject exception payloads, wrong CRS, incomplete pages and wrong locations."""
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("WFS response exceeded limit")
    data = json.loads(payload)
    if data.get("type") != "FeatureCollection":
        raise ValueError("Response is not a GeoJSON FeatureCollection")
    crs = (data.get("crs") or {}).get("properties", {}).get("name", "")
    if not crs.endswith("::6708") and crs != NATIVE_CRS:
        raise ValueError("Unexpected WFS coordinates: " + crs)
    features = data.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError(f"No features for {layer}; do not interpret as building absence")
    total = data.get("totalFeatures")
    if not isinstance(total, int) or total != len(features):
        raise ValueError(f"Incomplete page or unconfirmed count: {total} / {len(features)}")
    if total >= MAX_FEATURES:
        raise ValueError("Query too broad; features may be truncated")
    bounds_shape = shapely.box(*bounds)
    ids = set()
    for feature in features:
        fid = feature.get("id")
        if not isinstance(fid, str) or not fid.startswith(layer + ".") or fid in ids:
            raise ValueError("Bad/duplicate feature ID")
        ids.add(fid)
        geom = shapely.from_geojson(json.dumps(feature.get("geometry")))
        if geom.is_empty or not geom.is_valid:
            raise ValueError("Bad geometry " + fid)
        if not geom.intersects(bounds_shape):
            raise ValueError("Geometry not in native CRS BBOX " + fid)
    return data


def fetch(directory: Path, *, radius=DEFAULT_RADIUS_M):
    if not 30 <= radius <= 500 or directory.exists():
        raise ValueError("Out-of-range radius or output directory exists")
    transformer = Transformer.from_crs(4326, 6708, always_xy=True, allow_ballpark=False)
    e, n = transformer.transform(*CENTER_WGS84)
    bounds = (e - radius, n - radius, e + radius, n + radius)
    base = directory.with_name(directory.name + ".partial")
    if base.exists():
        raise FileExistsError("Unfinished previous run exists: " + str(base))
    base.mkdir(parents=True)
    summary = {
        "source": "Regione autonoma Friuli Venezia Giulia — official EDIFICI WFS",
        "service": WFS,
        "license_note": "Check the dataset-specific terms before republishing; raw responses remain local",
        "attribution": "Regione autonoma Friuli Venezia Giulia",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "center_wgs84_lon_lat": list(CENTER_WGS84),
        "native_crs": NATIVE_CRS,
        "native_bbox_e_n": list(bounds),
        "radius_m": radius,
        "layers": {},
        "status": "complete",
    }
    for layer in LAYERS:
        params = query_parameters(layer, bounds)
        url = WFS + "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"User-Agent": "ViaggioSoffumbergo/1.0 (non-commercial geodata QA)", "Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=35) as response:
            if response.status != 200 or "json" not in response.headers.get("Content-Type", ""):
                raise ValueError("WFS did not return GeoJSON")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        data = validate_snapshot(raw, layer, bounds)
        filename = layer + ".geojson"
        (base / filename).write_bytes(raw)
        summary["layers"][layer] = {
            "url": url,
            "filename": filename,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "features": len(data["features"]),
            "native_crs": data["crs"]["properties"]["name"],
        }
    (base / "manifest.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    base.rename(directory)
    print(json.dumps({"output": str(directory), "native_bbox": list(bounds), "layer_counts": {
        x: y["features"] for x, y in summary["layers"].items()}}, indent=2))
    return summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--radius-m", type=float, default=DEFAULT_RADIUS_M)
    a = p.parse_args()
    fetch(a.output.resolve(), radius=a.radius_m)


if __name__ == "__main__":
    main()
