#!/usr/bin/env python3
"""Validate a local FVG Arc/Info ASCII DTM and record its provenance.

The tool does NOT download LiDAR, convert vertical datums, or infer road heights.
No GDAL/QGIS dependency: usable for regional *.asc/.grd ASCII grids.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "build/geodata/fvg/dtm_catalog.json"
CRS_ALLOWED = ("EPSG:7792", "EPSG:6708", "EPSG:3004")
VERTICAL_ALLOWED = ("unknown", "orthometric", "ellipsoidal")


def _number(value, field):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {field}") from exc
    if not math.isfinite(result):
        raise ValueError(f"Nonfinite {field}")
    return result


def inspect_ascii_grid(file_path):
    """Read raster line by line; fail closed on corrupt header or missing rows."""
    path = Path(file_path)
    allowed = {"ncols", "nrows", "xllcorner", "yllcorner",
               "xllcenter", "yllcenter", "cellsize", "nodata_value"}
    header = {}
    minz = maxz = None
    valid = missing = 0
    with path.open("r", encoding="utf-8-sig") as fh:
        # ESRI ASCII files normally supply 6 header fields; permit absence of NODATA.
        first_data = None
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            parts = line.split()
            key = parts[0].lower()
            if key not in allowed:
                first_data = line
                break
            if len(parts) != 2 or key in header:
                raise ValueError("Duplicate/malformed ASCII grid header")
            header[key] = _number(parts[1], key)
        required = {"ncols", "nrows", "cellsize"}
        if not required.issubset(header) or not ({"xllcorner", "xllcenter"} & header.keys()) or not ({"yllcorner", "yllcenter"} & header.keys()):
            raise ValueError("Incomplete ESRI ASCII grid header")
        if ("xllcorner" in header) == ("xllcenter" in header) or ("yllcorner" in header) == ("yllcenter" in header):
            raise ValueError("Ambiguous ASCII grid corner/center positioning")
        ncol = header["ncols"]
        nrow = header["nrows"]
        if ncol <= 0 or nrow <= 0 or ncol > 100000 or nrow > 100000 or not ncol.is_integer() or not nrow.is_integer():
            raise ValueError("Invalid grid dimensions")
        ncol, nrow = int(ncol), int(nrow)
        cell = header["cellsize"]
        if not 0 < cell <= 10000:
            raise ValueError("Invalid grid resolution")
        nodata = header.get("nodata_value")
        if first_data is None:
            raise ValueError("Grid has no data rows")
        def rows():
            yield first_data
            for raw in fh:
                if raw.strip():
                    yield raw.strip()
        count = 0
        for line in rows():
            if count >= nrow:
                raise ValueError("Extra raster row")
            tokens = line.split()
            if len(tokens) != ncol:
                raise ValueError(f"Invalid column count at row {count + 1}")
            for token in tokens:
                z = _number(token, "raster cell")
                if nodata is not None and z == nodata:
                    missing += 1
                else:
                    valid += 1
                    minz = z if minz is None else min(z, minz)
                    maxz = z if maxz is None else max(z, maxz)
            count += 1
        if count != nrow or valid == 0:
            raise ValueError("Incomplete or completely empty raster")
    xmin = header["xllcorner"] if "xllcorner" in header else header["xllcenter"] - cell / 2
    ymin = header["yllcorner"] if "yllcorner" in header else header["yllcenter"] - cell / 2
    return {"ncols": ncol, "nrows": nrow, "cellsize_m": cell,
            "bounds_native_xy": [xmin, ymin, xmin + ncol * cell, ymin + nrow * cell],
            "nodata_value": nodata, "valid_cells": valid, "nodata_cells": missing,
            "grid_elevation_min": minz, "grid_elevation_max": maxz}


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def register(tile, source_url, horizontal_crs, vertical_datum,
             license_note="not_checked", catalog=DEFAULT_CATALOG, tile_id=None):
    if horizontal_crs not in CRS_ALLOWED:
        raise ValueError("Unsupported/undeclared horizontal CRS")
    if vertical_datum not in VERTICAL_ALLOWED:
        raise ValueError("Unsupported vertical datum")
    parsed = urlsplit(source_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Require a source HTTPS URL, not an invented local source")
    path, catalog = Path(tile).resolve(), Path(catalog)
    stats = inspect_ascii_grid(path)
    digest = sha256_file(path)
    ident = tile_id or path.stem
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,96}", ident):
        raise ValueError("Unsafe tile ID")
    record = {"tile_id": ident, "source_url": source_url,
              "input_file": str(path), "sha256": digest,
              "bytes": path.stat().st_size, "format": "ESRI_ASCII_GRID",
              "horizontal_crs": horizontal_crs,
              "native_xy_axis_order": "file columns / file rows (NOT guessed from EPSG labels)",
              "vertical_datum_operator_declared": vertical_datum,
              "vertical_metadata_verified": False,
              "license_note_operator_declared": license_note,
              "grid_not_road_surface": True,
              **stats}
    if catalog.exists():
        existing = json.loads(catalog.read_text(encoding="utf-8"))
        if existing.get("schema_version") != 1:
            raise ValueError("Unsupported terrain catalog version")
    else:
        existing = {"schema_version": 1, "dataset_type": "registered_local_dtm_tiles",
                    "route_elevation_status": "not_verified",
                    "terrain_surface_status": "input_grids_not_in_game",
                    "tiles": []}
    for item in existing["tiles"]:
        if item["tile_id"] == ident and item != record:
            raise ValueError("Tile ID conflict: refuse implicit overwrite")
    if not any(item["tile_id"] == ident for item in existing["tiles"]):
        existing["tiles"].append(record)
    existing["tiles"].sort(key=lambda x: x["tile_id"])
    catalog.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replace keeps the last good catalog when write fails.
    fd, tmp = tempfile.mkstemp(prefix=".dtm_catalog_", dir=catalog.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(existing, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(tmp, catalog)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path, help="Unzipped original regional *.asc tile")
    ap.add_argument("--source-url", required=True, help="Specific official download or dataset URL")
    ap.add_argument("--horizontal-crs", choices=CRS_ALLOWED, required=True)
    ap.add_argument("--vertical-datum", choices=VERTICAL_ALLOWED, default="unknown")
    ap.add_argument("--license-note", default="not_checked")
    ap.add_argument("--tile-id")
    ap.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = ap.parse_args()
    record = register(args.input, args.source_url, args.horizontal_crs,
                      args.vertical_datum, args.license_note, args.catalog, args.tile_id)
    print(f"Registered {record['tile_id']} ({record['ncols']}x{record['nrows']}, "
          f"cell {record['cellsize_m']} m). Datum not independently verified; "
          "no road elevation or Godot geometry inferred.")


if __name__ == "__main__":
    main()
