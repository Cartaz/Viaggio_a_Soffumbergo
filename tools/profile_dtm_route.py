#!/usr/bin/env python3
"""Sample an OSM 2D route against a local ESRI ASCII Digital Terrain Model.

This is NOT a roadway survey and NEVER produces Godot-ready coordinates.
Heights are raw DTM grid values, not WGS84 ellipsoidal road elevations.
For RDN2008/TM33NE (EPSG:6708), ESRI ASCII files store numeric x as
easting and y as northing: pyproj's always_xy is used explicitly.
"""
import argparse
from array import array
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_UNCOMPRESSED_ASCII_BYTES = 100_000_000


def load_asc_file(path, member=None):
    """Load a bounded ASCII Grid, fail closed on invalid header/data."""
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            names = [i for i in z.infolist() if i.filename.lower().endswith(".asc")
                     and not i.is_dir()]
            if member is None:
                if len(names) != 1:
                    raise ValueError("Archive must contain precisely one ASCII grid or use --member")
                member = names[0].filename
            info = z.getinfo(member)
            if info.file_size > MAX_UNCOMPRESSED_ASCII_BYTES:
                raise ValueError("ASCII grid exceeds safe in-memory size")
            with z.open(info) as fh:
                return parse_asc(fh)
    with path.open("rb") as fh:
        return parse_asc(fh)


def parse_asc(stream):
    header = {}
    for _ in range(6):
        tokens = stream.readline().decode("ascii").strip().split()
        if len(tokens) != 2:
            raise ValueError("Malformed ESRI ASCII Grid header")
        k, raw = tokens
        k = k.lower()
        if k in header:
            raise ValueError("Duplicate ASCII Grid header key")
        try:
            header[k] = float(raw)
        except ValueError as exc:
            raise ValueError("Non-numeric ASCII Grid header") from exc
    needed = {"ncols", "nrows", "xllcorner", "yllcorner", "cellsize", "nodata_value"}
    if set(header) != needed or any(not math.isfinite(v) for v in header.values()):
        raise ValueError("Expected finite corner-based ESRI ASCII Grid")
    nc, nr, step = header["ncols"], header["nrows"], header["cellsize"]
    if not nc.is_integer() or not nr.is_integer() or not (0 < nc <= 30000) or not (0 < nr <= 30000):
        raise ValueError("Invalid dimensions")
    nc, nr = int(nc), int(nr)
    if not 0 < step <= 100:
        raise ValueError("Invalid cellsize")
    if nc * nr > 15_000_000:
        raise ValueError("Grid too large for bounded standard-library reader; use GDAL")
    data = array("f")
    for row in range(nr):
        line = stream.readline()
        if not line:
            raise ValueError(f"Grid truncated at row {row}")
        tokens = line.decode("ascii").split()
        if len(tokens) != nc:
            raise ValueError(f"Unexpected column count on row {row}")
        values = [float(value) for value in tokens]
        if any(not math.isfinite(value) for value in values):
            raise ValueError("Nonfinite raster cell")
        data.extend(values)
    if stream.read(200).strip():
        raise ValueError("Unexpected trailing grid data")
    return {"ncols": nc, "nrows": nr, "cellsize": step,
            "xllcorner": header["xllcorner"], "yllcorner": header["yllcorner"],
            "nodata": header["nodata_value"], "data": data}


def sample_bilinear(grid, easting, northing):
    """Return None for outside/NoData instead of silently filling missing heights."""
    dx = (easting - grid["xllcorner"]) / grid["cellsize"] - .5
    top = grid["yllcorner"] + grid["nrows"] * grid["cellsize"]
    dy = (top - northing) / grid["cellsize"] - .5
    left, row = math.floor(dx), math.floor(dy)
    if not (0 <= left < grid["ncols"] - 1 and 0 <= row < grid["nrows"] - 1):
        return None
    a, b = dx - left, dy - row
    nc = grid["ncols"]
    d = grid["data"]
    v00, v10, v01, v11 = (d[row * nc + left], d[row * nc + left + 1],
                            d[(row + 1) * nc + left], d[(row + 1) * nc + left + 1])
    if any(abs(v - grid["nodata"]) < 1e-4 for v in (v00, v10, v01, v11)):
        return None
    return round((1-a)*(1-b)*v00 + a*(1-b)*v10 + (1-a)*b*v01 + a*b*v11, 3)


def profile(geojson, grid, source_url, archive_sha256, spacing_m=10, horizontal_crs="EPSG:6708"):
    """Interpolate 2D OSM route coordinates, NOT heights, and sample source DTM."""
    if horizontal_crs not in {"EPSG:6708", "EPSG:7792"}:
        raise ValueError("Only explicit RDN2008/TM33 grid supported")
    if not math.isfinite(spacing_m) or spacing_m < 1 or spacing_m > 100:
        raise ValueError("Invalid sampling step")
    if (geojson.get("route_status") != "topologically_connected_candidate_not_a_verified_driving_route"
            or geojson.get("usable_as_game_road") is not False):
        raise ValueError("Expected review-only 2D route candidate")
    from pyproj import Transformer
    transform = Transformer.from_crs("EPSG:4326", horizontal_crs, always_xy=True)
    segments, last_sector_endpoint = [], None
    overall = 0.
    for f in geojson["features"]:
        sector = f["properties"]["sector"]
        coords = f["geometry"]["coordinates"]
        if len(coords) < 2 or any(len(c) != 2 for c in coords):
            raise ValueError("Missing or 3D road coordinates")
        if last_sector_endpoint is not None and coords[0] != last_sector_endpoint:
            raise ValueError("Disconnected sector edges")
        last_sector_endpoint = coords[-1]
        projected = [transform.transform(float(lon), float(lat)) for lon, lat in coords]
        if any(not all(math.isfinite(x) for x in p) for p in projected):
            raise ValueError("Invalid coordinate transform")
        samples = []
        sum_dummy = 0.
        for i, (p, q) in enumerate(zip(projected, projected[1:])):
            distance = math.hypot(q[0] - p[0], q[1] - p[1])
            if distance <= 1e-8:
                continue
            n = math.ceil(distance / spacing_m)
            for t in range(0 if i == 0 else 1, n + 1):
                frac = t / n
                e = p[0] + (q[0] - p[0]) * frac
                n_ = p[1] + (q[1] - p[1]) * frac
                z = sample_bilinear(grid, e, n_)
                samples.append({"distance_along_sector_m": round(sum_dummy + distance*frac, 3),
                                "projected_e_m": round(e, 3),
                                "projected_n_m": round(n_, 3),
                                "dtm_raw_grid_value_m": z})
            sum_dummy += distance
        if not samples:
            raise ValueError("Empty sector sampling")
        count = sum(s["dtm_raw_grid_value_m"] is not None for s in samples)
        if count != len(samples):
            # Still preserve missing samples for inspection; don't approve coverage.
            pass
        vals = [s["dtm_raw_grid_value_m"] for s in samples if s["dtm_raw_grid_value_m"] is not None]
        length = round(sum_dummy, 3)
        overall += length
        segments.append({"sector": sector, "length_projected_m": length, "samples": samples,
                         "sample_count": len(samples), "valid_count": count,
                         "data_min": round(min(vals), 3) if vals else None,
                         "data_max": round(max(vals), 3) if vals else None})
        sum_dummy = 0.
    return {"schema_version": 1,
            "status": "REAL_DTM_SAMPLED_NOT_SURVEYED_ROAD",
            "coordinate_reference": horizontal_crs,
            "input_route": "OSM candidate 2D (unverified turns)",
            "source_url": source_url, "source_archive_sha256": archive_sha256,
            "horizontal_crs": horizontal_crs,
            "vertical_datum": "UNKNOWN_NOT_VERIFIED",
            "sampled_surface": "BARE_EARTH_DTM_NOT_ASPHALT",
            "height_units": "metres_as_stored_in_source_grid",
            "godot_ready": False, "road_slope_verified": False,
            "road_width_verified": False, "step_m_max": spacing_m,
            "total_length_projected_m": round(overall, 3),
            "all_samples_present": all(s["sample_count"] == s["valid_count"] for s in segments),
            "sectors": segments}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--route", type=Path, default=ROOT/"data/geography/circuito_osm_candidate_20261020.geojson")
    ap.add_argument("--ascii", required=True, type=Path)
    ap.add_argument("--member", help="Specify ASCII grid archive member for multi-file ZIP")
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--horizontal-crs", choices=["EPSG:6708", "EPSG:7792"], required=True)
    ap.add_argument("--spacing-m", type=float, default=10.)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    grid = load_asc_file(args.ascii, args.member)
    with args.ascii.open("rb") as fh:
        h = hashlib.file_digest(fh, "sha256").hexdigest()
    result = profile(json.loads(args.route.read_text(encoding="utf-8")),
                     grid, args.source_url, h, args.spacing_m, args.horizontal_crs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for s in result["sectors"]:
        print(f"{s['sector']}: {s['valid_count']}/{s['sample_count']} DTM samples; "
              f"grid min={s['data_min']}, max={s['data_max']}")
    print("Real bare-earth DTM, vertical datum unverified; NOT game road or surveyed grade.")


if __name__ == "__main__":
    main()
