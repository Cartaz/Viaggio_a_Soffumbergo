#!/usr/bin/env python3
"""User-supplied FVG 0.5m ellipsoidal DTM: strict mosaicking and provisional 3D.

Original ZIP is not committed to public GitHub. Uses numpy, rasterio, trimesh
(offline processing dependencies). Output EPSG:6708 0.5m float32 GeoTIFF and
a 4m ground-only GLB. NOT a surveyed or driveable road/scene.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

TILES = ("06701210", "06701211", "06701214", "06701215")
FOOTPRINTS = {
    "06701210": (375240, 5112525, 376140, 5113365),
    "06701211": (376060, 5112525, 376960, 5113365),
    "06701214": (375240, 5111765, 376140, 5112605),
    "06701215": (376060, 5111765, 376960, 5112605),
}
KNOWN_ARCHIVE_SHA256 = "bd715cd7c9b3820646f93f9e918cab1159950f47c2df5fc39e0218fc564a6a14"


def read_grids(zip_path):
    source = Path(zip_path)
    with source.open("rb") as fh:
        digest = hashlib.file_digest(fh, "sha256").hexdigest()
    if digest != KNOWN_ARCHIVE_SHA256:
        raise ValueError("Unknown LiDAR source ZIP: checksum changed; review its provenance first")
    import numpy as np
    grids = {}
    with zipfile.ZipFile(source) as archive:
        wanted = {f"Ell_DTM_{code}.asc" for code in TILES}
        if len(archive.infolist()) != 4 or set(archive.namelist()) != wanted:
            raise ValueError("Expected exactly four named ellipsoidal ASC raster files")
        if archive.testzip() is not None:
            raise ValueError("Corrupted ZIP entry")
        for code in TILES:
            name = f"Ell_DTM_{code}.asc"
            info = archive.getinfo(name)
            if not 18_000_000 < info.file_size < 24_000_000:
                raise ValueError("Unexpected decompressed file size: " + name)
            with archive.open(info) as fh:
                header = {}
                for _ in range(6):
                    fields = fh.readline().decode("ascii").strip().split()
                    if len(fields) != 2 or fields[0].lower() in header:
                        raise ValueError("Invalid ASC header")
                    header[fields[0].lower()] = float(fields[1])
                if set(header) != {"ncols", "nrows", "xllcenter", "yllcenter",
                                   "cellsize", "nodata_value"}:
                    raise ValueError("Unknown ASC header layout")
                if (header["ncols"], header["nrows"], header["cellsize"],
                    header["nodata_value"]) != (1800, 1680, 0.5, -9999):
                    raise ValueError("Wrong grid dimensions, step or nodata")
                xmin, ymin = header["xllcenter"] - .25, header["yllcenter"] - .25
                if (xmin, ymin, xmin + 900, ymin + 840) != FOOTPRINTS[code]:
                    raise ValueError("Raster footprint contradicts official WFS index")
                values = np.fromstring(fh.read().decode("ascii"), sep=" ", dtype=np.float32)
                if values.size != 1800 * 1680 or not np.isfinite(values).all():
                    raise ValueError("Invalid or truncated ASCII grid")
                if np.any(values == -9999):
                    raise ValueError("Real source has unexpected NoData cells")
                grids[code] = values.reshape((1680, 1800))
    return grids, digest


def mosaic(grids):
    import numpy as np
    result = np.full((3200, 3440), np.nan, dtype=np.float32)
    repeats = 0
    for code in TILES:
        x0, _, _, y1 = FOOTPRINTS[code]
        row = int((5113365 - y1) / .5)
        col = int((x0 - 375240) / .5)
        target = result[row:row + 1680, col:col + 1800]
        values = grids[code]
        covered = np.isfinite(target)
        repeats += int(covered.sum())
        if covered.any() and np.any(target[covered] != values[covered]):
            raise ValueError("Conflicting elevations in overlapping raster tiles")
        target[~covered] = values[~covered]
    if np.isnan(result).any():
        raise ValueError("Uncovered cells in 0.5m terrain mosaic")
    return result, repeats


def export_geotiff(path, terrain):
    import rasterio
    from rasterio.transform import from_origin
    with rasterio.open(path, "w", driver="GTiff", width=3440, height=3200,
                       count=1, crs="EPSG:6708", transform=from_origin(
                           375240, 5113365, .5, .5), dtype="float32",
                       nodata=-9999, tiled=True, blockxsize=256, blockysize=256,
                       compress="DEFLATE", predictor=3) as output:
        output.write(terrain, 1)


def export_glb(path, terrain):
    import numpy as np
    import trimesh
    # Provisional Godot frame: +X East, +Y up, +Z South. Horizontal EPSG:6708;
    # 720m is a LOCAL DISPLAY ORIGIN, not a vertical datum transformation.
    rr = np.unique(np.r_[np.arange(0, 3200, 8), 3199])
    cc = np.unique(np.r_[np.arange(0, 3440, 8), 3439])
    col, row = np.meshgrid(cc, rr)
    vertices = np.column_stack((
        (375240.25 + .5 * col - 375920).ravel(),
        (terrain[np.ix_(rr, cc)] - 720).ravel(),
        (5112728 - (5113364.75 - .5 * row)).ravel(),
    )).astype("float32")
    i = np.arange(vertices.shape[0]).reshape(row.shape)
    nw, ne = i[:-1, :-1].ravel(), i[:-1, 1:].ravel()
    sw, se = i[1:, :-1].ravel(), i[1:, 1:].ravel()
    # glTF uses counter-clockwise fronts; trimesh normals point +Y.
    faces = np.vstack((np.column_stack((nw, sw, ne)),
                       np.column_stack((ne, sw, se))))
    trimesh.Trimesh(vertices=vertices, faces=faces, process=False).export(path)
    return {"vertices": len(vertices), "triangles": len(faces),
            "approx_grid_step_m": 4, "origin_ENH_m": [375920, 5112728, 720],
            "status": "provisional_ground_visual_only_not_road"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    terrain, source_sha = None, None
    grids, source_sha = read_grids(args.source)
    terrain, repeated = mosaic(grids)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raster = args.output_dir / "Valle_Soffumbergo_DTM_LiDAR_05m_ellissoidico_EPSG6708.tif"
    blockout = args.output_dir / "Valle_Soffumbergo_terreno_blocco_4m.glb"
    export_geotiff(raster, terrain)
    mesh = export_glb(blockout, terrain)
    report = {"schema_version": 1, "source_zip_sha256": source_sha,
              "source_archives_committed": False,
              "ground_only": True, "road_surface_verified": False,
              "horizontal_crs": "EPSG:6708",
              "vertical_reference": "ellipsoidal per original Ell_DTM filenames",
              "ellipsoidal_to_orthometric_transform_applied": False,
              "resolution_m": .5, "mosaic_unique_cells": terrain.size,
              "overlap_duplicate_cells": repeated, "overlap_max_error_m": 0.,
              "nodata_cells": 0, "bounds_EN_m": [375240, 5111765, 376960, 5113365],
              "game_ready": False, "glb": mesh,
              "source_license_for_redistribution": "verify with regional download metadata"}
    (args.output_dir / "Valle_LiDAR05_QC_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
