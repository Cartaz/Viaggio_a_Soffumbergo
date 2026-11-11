"""Verified acquisition of Ell_DBM, Ell_DSMfirst and Ell_DSMlast for route DTM tiles.

Only reads the original Eagle ZIP. The 41 existing DTM rasters are verified
byte-for-byte against ZIP members, never replaced; three matching ellipsoidal
surfaces per tile are extracted locally with CRC/SHA-256 and header alignment.
If any member fails, leaves a .partial output that is NOT a completed dataset.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

from audit_mont_joanes_height_sources import parse_ascii_header,file_hash,REGIONAL_SOURCE
from inspect_eagle_bundle import checked_members

ROOT=Path(__file__).resolve().parents[1]
DTM_ROOT=ROOT/"data/lidar/raw_20261020"
ZIP_DEFAULT=Path(r"C:\Users\Casa\Downloads\download-20261114083722230.zip")
ROLES=("DBM","DSM_FIRST","DSM_LAST")
SOURCE_URL="https://eaglefvg.regione.fvg.it/eagle/main.aspx?configuration=guest"


def expected_basename(tile, role):
    if not re.fullmatch(r"\d{8}",tile):
        raise ValueError("Invalid LiDAR tile identifier")
    prefix={"DTM":"Ell_DTM_","DBM":"Ell_DBM_",
            "DSM_FIRST":"Ell_DSMfirst_","DSM_LAST":"Ell_DSMlast_"}[role]
    return prefix+tile+".asc"


def matching_members(zip_file, tiles):
    all_entries=list(checked_members(zip_file.infolist()))
    by_name={}
    for x in all_entries:
        basename=PurePosixPath(x.filename).name
        if basename in by_name:
            raise ValueError("Duplicate filename in extracted source: "+basename)
        by_name[basename]=x
    matrix={}
    for tile in tiles:
        matrix[tile]={}
        for role in ("DTM",)+ROLES:
            name=expected_basename(tile,role)
            if name not in by_name:
                raise ValueError(f"Missing product {role} for route tile {tile}")
            matrix[tile][role]=by_name[name]
    return matrix


def extract_verified(source_zip:Path, original_dtm_dir:Path, output:Path):
    source_zip=source_zip.resolve()
    original_dtm_dir=original_dtm_dir.resolve()
    output=output.resolve()
    if output.exists():
        raise FileExistsError("Output already exists: "+str(output))
    pending=output.with_name(output.name+".partial")
    if pending.exists():
        raise FileExistsError("Unfinished source acquisition present: "+str(pending))
    if not source_zip.exists() or not zipfile.is_zipfile(source_zip):
        raise ValueError("Original source ZIP is missing/incomplete")
    if list(source_zip.parent.glob(source_zip.stem+"*.zip.part")):
        raise ValueError("Original source ZIP is still downloading")
    original_files=sorted(original_dtm_dir.glob("Ell_DTM_*.asc"))
    if not original_files:
        raise FileNotFoundError("No original route DTM tiles found")
    tiles=[f.stem.split("_")[-1] for f in original_files]
    if len(tiles)!=len(set(tiles)):
        raise ValueError("Duplicate original DTM tiles")
    original_by_tile=dict(zip(tiles,original_files))
    with zipfile.ZipFile(source_zip,"r") as z:
        matrix=matching_members(z,tiles)
        pending.mkdir(parents=True)
        summary={
            "status":"partial",
            "source_archive":str(source_zip),
            "source_archive_size_bytes":source_zip.stat().st_size,
            "source_catalog_url":REGIONAL_SOURCE,
            "source_download_url":SOURCE_URL,
            "horizontal_crs":"EPSG:6708",
            "vertical_datum":"ellipsoidal",
            "cell_size_m":0.5,
            "route_tile_count":len(tiles),
            "products_per_tile":list(ROLES),
            "tiles":{}
        }
        for i,tile in enumerate(tiles,1):
            expected=original_by_tile[tile]
            dtm=parse_ascii_header(expected)
            dtm_layout=(dtm.rows,dtm.cols,dtm.x_center,dtm.y_center,dtm.cell)
            known_sha=file_hash(expected)
            entry=matrix[tile]["DTM"]
            zip_hash=hashlib.sha256()
            with z.open(entry) as source:
                for block in iter(lambda:source.read(2*1024*1024),b""):
                    zip_hash.update(block)
            if known_sha!=zip_hash.hexdigest():
                raise ValueError(f"Original DTM does NOT match archive: {tile}")
            t={
                "original_dtm":{"path":str(expected),"sha256":known_sha,
                    "zip_crc32":f"{entry.CRC:08x}"},
                "products":{}
            }
            for role in ROLES:
                info=matrix[tile][role]
                f=pending/expected_basename(tile,role)
                temp=f.with_suffix(f.suffix+".part")
                hash_=hashlib.sha256()
                size=0
                with z.open(info) as stream,temp.open("xb") as sink:
                    for block in iter(lambda:stream.read(2*1024*1024),b""):
                        sink.write(block)
                        size+=len(block)
                        hash_.update(block)
                if size!=info.file_size:
                    raise ValueError(f"Archive member decompressed size mismatch: {tile} {role}")
                temp.rename(f)
                raster=parse_ascii_header(f)
                layout=(raster.rows,raster.cols,raster.x_center,raster.y_center,raster.cell)
                if layout!=dtm_layout:
                    raise ValueError(f"DSM/DBM raster misaligned with the native DTM: {tile} {role}")
                t["products"][role]={
                    "original_basename":f.name,
                    "relative_path":f.name,
                    "zip_path":info.filename,
                    "zip_crc32":f"{info.CRC:08x}",
                    "sha256":hash_.hexdigest(),
                    "bytes":size
                }
            summary["tiles"][tile]=t
            # Progress is safe: summary isn't marked verified until all tiles pass.
            print(f"VALIDATED {i}/{len(tiles)} TILE {tile} (DTM identical + DBM/DSM CRC/SHA-256)",flush=True)
    summary["status"]="complete"
    (pending/"manifest.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    pending.rename(output)
    print(json.dumps({"status":"complete","route_tiles":len(tiles),
                      "new_rasters":sum(len(t["products"]) for t in summary["tiles"].values()),
                      "out":str(output)},ensure_ascii=False))
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,default=ZIP_DEFAULT)
    p.add_argument("--dtm-dir",type=Path,default=DTM_ROOT)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    extract_verified(a.archive,a.dtm_dir,a.output)


if __name__=="__main__":
    main()
