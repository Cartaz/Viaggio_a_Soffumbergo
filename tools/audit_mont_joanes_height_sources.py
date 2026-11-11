"""Evidence-only altimetry at documented Mont Joanes chassis/footprint hotspots.

Use official ellipsoidal EPSG:6708 gridded values. Never equate bare-earth
DTM with building roof, wall, or game collision. DSM/DBM are *optional* and
only accepted with a user-provided SHA-256 + source/datum manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import NamedTuple

import numpy as np
from pyproj import Transformer, network

ROOT = Path(__file__).resolve().parents[1]
DTM_DIR = ROOT / "data/lidar/raw_20261020"
REGIONAL_HOTSPOTS = ROOT / "results/fvg_official_buildings/full_lap_20261107_v1/report.json"
OSM_HOTSPOTS = ROOT / "results/building_context/f437_swept_chassis_20261106_v1/report.json"
REGIONAL_SOURCE = "https://irdat.regione.fvg.it/consultatore-dati-ambientali-territoriali/detail/irdat/dataset/11826"
EPSG = "EPSG:6708"


class AsciiGrid(NamedTuple):
    path: Path
    rows: int
    cols: int
    x_center: float
    y_center: float
    cell: float
    nodata: float
    header_sha256: str

    def covers(self, east, north):
        return (self.x_center <= east <= self.x_center + (self.cols-1)*self.cell
                and self.y_center <= north <= self.y_center + (self.rows-1)*self.cell)


def file_hash(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def parse_ascii_header(path: Path) -> AsciiGrid:
    """Support native ESRI ASCII xllcenter or xllcorner, not arbitrary rasters."""
    path = Path(path)
    fields = {}
    with path.open("rb") as f:
        raw_lines = [f.readline() for _ in range(6)]
    for raw in raw_lines:
        line = raw.decode("ascii", "strict").strip().split()
        if len(line) != 2 or line[0].lower() in fields:
            raise ValueError(f"Bad ESRI ASCII header: {path}")
        fields[line[0].lower()] = float(line[1])
    required = {"ncols", "nrows", "cellsize", "nodata_value"}
    if not required <= fields.keys():
        raise ValueError("Missing ESRI ASCII header fields")
    if any((not math.isfinite(v)) for v in fields.values()):
        raise ValueError("Nonfinite ESRI ASCII header")
    cols, rows = int(fields["ncols"]), int(fields["nrows"])
    if cols != fields["ncols"] or rows != fields["nrows"] or cols < 2 or rows < 2:
        raise ValueError("Invalid ASC grid dimensions")
    cell = fields["cellsize"]
    if not (cell == 0.5):
        raise ValueError(f"Expected official 0.5m grid, got {cell}")
    if ("xllcenter" in fields) != ("yllcenter" in fields):
        raise ValueError("Inconsistent x/y registration")
    if ("xllcorner" in fields) != ("yllcorner" in fields):
        raise ValueError("Inconsistent x/y registration")
    if "xllcenter" in fields and "xllcorner" in fields:
        raise ValueError("Ambiguous registration")
    if "xllcenter" in fields:
        east, north = fields["xllcenter"], fields["yllcenter"]
    elif "xllcorner" in fields:
        east, north = fields["xllcorner"] + cell/2, fields["yllcorner"]+cell/2
    else:
        raise ValueError("ASC missing origin")
    digest = hashlib.sha256(b"".join(raw_lines)).hexdigest()
    return AsciiGrid(path, rows, cols, east, north, cell, fields["nodata_value"], digest)


def sample_grid(grid: AsciiGrid, east: float, north: float):
    """Bilinear ground-height sample at a point within cell-center coverage."""
    if not grid.covers(east, north):
        return None
    # ESRI ASCII values begin at the NORTHWEST (upper-left) cell center.
    col = (east-grid.x_center)/grid.cell
    row = grid.rows - 1 - (north-grid.y_center)/grid.cell
    x0, y0 = min(int(math.floor(col)), grid.cols-2), min(int(math.floor(row)), grid.rows-2)
    dx, dy = col-x0, row-y0
    if not (0 <= dx <= 1+1e-8 and 0 <= dy <= 1+1e-8):
        raise ValueError("ASC fractional index outside expected bounds")
    # Read only the two data rows needed, not the entire 20MB raster.
    pairs = []
    with grid.path.open("r", encoding="ascii") as inp:
        for _ in range(6):
            next(inp)
        for i, line in enumerate(inp):
            if i not in (y0, y0+1):
                continue
            cells = line.split()
            if len(cells) != grid.cols:
                raise ValueError(f"Unexpected ASC data columns in row {i}: {len(cells)}")
            pairs.append((i, float(cells[x0]), float(cells[x0+1])))
            if len(pairs)==2:
                break
    if len(pairs)!=2 or pairs[0][0]!=y0 or pairs[1][0]!=y0+1:
        raise ValueError("ASC rows missing")
    z = np.asarray([[pairs[0][1], pairs[0][2]], [pairs[1][1], pairs[1][2]]])
    if not np.isfinite(z).all() or np.any(np.isclose(z, grid.nodata)):
        return None
    return float((1-dy)*((1-dx)*z[0,0]+dx*z[0,1])
                 + dy*((1-dx)*z[1,0]+dx*z[1,1]))


def inspect_optional_manifest(manifest_path: Path | None):
    """No implicit DSM=DTM fallbacks, vertical conversions, or online scraping."""
    if manifest_path is None:
        return {}
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("horizontal_crs") != EPSG or manifest.get("vertical_datum") != "ellipsoidal":
        raise ValueError("Optional sources must use verified EPSG:6708 ellipsoidal heights")
    if manifest.get("source_catalog_url") != REGIONAL_SOURCE:
        raise ValueError("Optional sources must declare specific official dataset")
    outputs = {}
    for role in ("DBM", "DSM_FIRST", "DSM_LAST"):
        entry = manifest.get("products", {}).get(role)
        if entry is None:
            continue
        if entry.get("product") != role:
            raise ValueError("Raster product role does not match")
        if not entry.get("source_download_url") or not entry.get("original_basename"):
            raise ValueError("Raster source provenance required")
        file = Path(entry["path"])
        if file.name != entry["original_basename"] or not file.is_file():
            raise ValueError("Raster path does not match recorded original basename")
        if (not file.name.lower().startswith("ell_")
                or ("dbm" if role=="DBM" else "dsm") not in file.name.lower()):
            raise ValueError("Expected an original Ell_* raster with the correct product type")
        if role.startswith("DSM_"):
            label = re.search(r"dsm[_-]?(first|primo|last|ultimo)",file.name.lower())
            expected = {"DSM_FIRST":{"first","primo"},"DSM_LAST":{"last","ultimo"}}[role]
            if label is None or label.group(1) not in expected:
                raise ValueError("DSM return type does not match manifest role")
        if file_hash(file) != entry["sha256"]:
            raise ValueError("Raster SHA-256 mismatch; do not use unverified source")
        grid = parse_ascii_header(file)
        outputs[role] = (grid, entry["sha256"])
    if not outputs:
        raise ValueError("Manifest does not include any regional surface product")
    return outputs


def points_from_reports(regional: dict, osm: dict):
    if regional.get("native_build_id") != "f4373a62b482" or not regional.get("complete"):
        raise ValueError("Wrong candidate native audit")
    if osm.get("build_id") != regional["native_build_id"] or not osm.get("diagnostic_completed"):
        raise ValueError("Wrong OSM audit")
    points=[]
    for case in regional["regional_layers"]["DBS_EDIFICATO"]["cases"]:
        points.append({"source_id":case["regional_id"],
                       "source":"DBTsped 2017-2020 × native chassis",
                       "wgs84_lat_lon":case["approx_peak_wgs84_lat_lon"]})
    for case in osm["cases"]:
        if case["source_id"] not in ("way/36158227","way/36158219"):
            continue
        points.append({"source_id":case["source_id"],
                       "source":"OSM 2026 × native chassis",
                       "wgs84_lat_lon":case["peak_vehicle_center_wgs84"]})
    return points


def audit(dtm_dir: Path, regional_path: Path, osm_path: Path, output: Path,
          optional_manifest: Path | None = None):
    if output.exists():
        raise FileExistsError("Never overwrite a prior DTM/DSM/DBM audit")
    regional = json.loads(regional_path.read_text(encoding="utf-8"))
    osm = json.loads(osm_path.read_text(encoding="utf-8"))
    target_points = points_from_reports(regional, osm)
    grids=[]
    for file in sorted(dtm_dir.glob("Ell_DTM_*.asc")):
        grids.append(parse_ascii_header(file))
    if not grids:
        raise FileNotFoundError("No original Ell_DTM 0.5m ASCII files")
    optional = inspect_optional_manifest(optional_manifest)
    network.set_network_enabled(False)
    trans = Transformer.from_crs(4326, 6708, always_xy=True, allow_ballpark=False)
    result=[]
    coverage = {}
    for point in target_points:
        lat,lon = point["wgs84_lat_lon"]
        e,n = trans.transform(lon,lat)
        covering = [g for g in grids if g.covers(e,n)]
        candidates=[(g,sample_grid(g,e,n)) for g in covering]
        available=[(g,z) for g,z in candidates if z is not None]
        if len(available) > 1 and max(z for _,z in available)-min(z for _,z in available)>0.03:
            raise ValueError("Overlapping DTM files disagree by >3cm at " + point["source_id"])
        picked = min(available,key=lambda pair:pair[0].path.name) if available else None
        surface = {}
        for role,(grid,checksum) in optional.items():
            z = sample_grid(grid,e,n)
            surface[role] = {
                "ellipsoidal_height_m":z,
                "relative_to_dtm_m":None if z is None or picked is None else z-picked[1],
                "source_sha256":checksum,
                "grid_file":grid.path.name,
                "covers_sample":z is not None
            }
        result.append({
            **point,
            "native_east_m":e, "native_north_m":n,
            "dtm_covering_tiles":[g.path.name for g in covering],
            "dtm_ground_ellipsoidal_m":picked[1] if picked else None,
            "selected_dtm_tile":picked[0].path.name if picked else None,
            "surface_products":surface,
            "physical_ground_wall_or_roof_height_confirmed":False,
        })
        for grid in covering:
            coverage[grid.path.name] = file_hash(grid.path)
    report = {
        "status":"complete" if optional else "dtm_ground_only_dsm_dbm_missing",
        "candidate_build":"f4373a62b482",
        "source":"RAFVG LiDAR 2017-2020 ellipsoidal DTM 0.50 m",
        "source_catalog_url":REGIONAL_SOURCE,
        "horizontal_crs":EPSG,"vertical_datum":"ellipsoidal",
        "regional_hotspots_report_sha256":file_hash(regional_path),
        "osm_hotspots_report_sha256":file_hash(osm_path),
        "tile_sha256":coverage,
        "optional_manifest":str(optional_manifest) if optional_manifest else None,
        "optional_products_verified":sorted(optional),
        "hotspots_checked":len(result),
        "dtm_coverage_count":sum(p["dtm_ground_ellipsoidal_m"] is not None for p in result),
        "points":result,
        "no_game_assets_modified":True,
        "limitations":"DTM is bare earth: not asphalt or building. DSM/DBM absent unless verified manifest explicitly supplied. Ellipsoidal heights are NOT orthometric heights; nothing estimates building walls or native 3D collisions."
    }
    output.mkdir(parents=True)
    (output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":report["status"],"coverage":report["dtm_coverage_count"],
                      "samples":[{"id":p["source_id"],"height_m":p["dtm_ground_ellipsoidal_m"],
                                  "tile":p["selected_dtm_tile"]} for p in result],
                      "output":str(output)},ensure_ascii=False,indent=2))
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dtm-dir",type=Path,default=DTM_DIR)
    ap.add_argument("--regional-report",type=Path,default=REGIONAL_HOTSPOTS)
    ap.add_argument("--osm-report",type=Path,default=OSM_HOTSPOTS)
    ap.add_argument("--optional-surfaces-manifest",type=Path)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    audit(a.dtm_dir.resolve(),a.regional_report.resolve(),a.osm_report.resolve(),
          a.output.resolve(),a.optional_surfaces_manifest.resolve() if a.optional_surfaces_manifest else None)


if __name__=="__main__":
    main()
