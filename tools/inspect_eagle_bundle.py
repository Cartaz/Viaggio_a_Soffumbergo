r"""Inspect the downloaded Eagle.fvg ZIP safely, without unpacking bulk data.

Usage (after Firefox completed its .part download):
    python tools/inspect_eagle_bundle.py --archive "C:\Users\Casa\Downloads\download-....zip" --output results/eagle_bundle/report_v1

Optional --extract-targets extracts ONLY raster candidates for original LiDAR
tile 06701307 to a new folder, checking ZIP CRC and preserving source names.
Raw regional data is kept local under ignored results/.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TILE = "06701307"
ALLOWED_EXTS = {".asc", ".tif", ".tiff", ".las", ".laz", ".xyz", ".bil", ".img"}
MAX_INFLATE_BYTES = 150 * 1024**3
MAX_COMPRESSION_RATIO = 1000


def safe_name(name: str) -> str:
    """Reject absolute, traversal, illegal and platform-dependent ZIP paths."""
    if not name or "\x00" in name or "\\" in name or name.startswith(("/", "//")):
        raise ValueError(f"Unsafe archive path {name!r}")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        # Allow trailing "/" for explicit folder only (folders are skipped).
        if not (name.endswith("/") and all(p not in ("", ".", "..") for p in parts[:-1]) and parts[-1] == ""):
            raise ValueError(f"Unsafe archive path {name!r}")
    if re.match(r"^[A-Za-z]:", name) or any(":" in p for p in parts):
        raise ValueError(f"Windows drive/ADS path {name!r}")
    if any(p.rstrip(" .") != p for p in parts if p):
        raise ValueError(f"Windows ambiguous archive path {name!r}")
    return name


def classify_entry(name: str) -> dict:
    s = name.upper()
    # Classify strictly from observed names; no implied surface product.
    match = re.search(r"(?<![A-Z])(?:ELL|ORT)?[_\-\s]*(DSM|DBM|DTM)(?:[_\-\s]*(FIRST|LAST|PRIMO|ULTIMO|1ST|2ND))?(?![A-Z])", s)
    if match:
        role = match.group(1)
        subtype = match.group(2) or "unspecified"
    elif re.search(r"(?<![A-Z])LAS|LAZ(?![A-Z])", s):
        role, subtype = "POINT_CLOUD", "not_surface_raster"
    else:
        role, subtype = "OTHER", "unclassified"
    datum = "ellipsoidal" if re.search(r"(?:^|[/_\s])ELL(?:[_\s-]|$)|ELLISSOID", s) else (
        "orthometric" if re.search(r"(?:^|[/_\s])ORT(?:[_\s-]|$)|ORTOMETR", s) else "unknown")
    return {"role_guess":role, "subtype_guess":subtype, "datum_guess":datum,
            "filename":PurePosixPath(name).name}


def checked_members(entries: list[zipfile.ZipInfo]):
    seen = set()
    total = 0
    for info in entries:
        name = safe_name(info.filename)
        key = name.rstrip("/").casefold()
        if key in seen:
            raise ValueError(f"Duplicate/case-conflicting archive member: {name!r}")
        seen.add(key)
        if info.is_dir():
            continue
        if stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
            raise ValueError(f"Archive symlink forbidden: {name!r}")
        if info.flag_bits & 0x1:
            raise ValueError(f"Encrypted ZIP member unsupported: {name!r}")
        if info.file_size < 0 or info.compress_size < 0:
            raise ValueError(f"Invalid ZIP member size: {name!r}")
        if info.file_size > MAX_INFLATE_BYTES:
            raise ValueError(f"Excessive single file size: {name!r}")
        ratio = info.file_size / max(1, info.compress_size)
        if ratio > MAX_COMPRESSION_RATIO:
            raise ValueError(f"Abnormal compression ratio: {name!r}")
        total += info.file_size
        yield info


def sha256(path: Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(8*1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect(archive: Path, output: Path, *, target_tile=DEFAULT_TILE, extract=False):
    archive=archive.resolve()
    if output.exists():
        raise FileExistsError(f"Preserve earlier inventory: {output}")
    if not archive.is_file() or not archive.name.lower().endswith(".zip"):
        raise FileNotFoundError(f"No completed zip found: {archive}")
    # Firefox uses temporary .zip.part; do not open a moving download.
    if any(archive.parent.glob(archive.name + ".part")) or any(
        archive.parent.glob(archive.stem + "*.zip.part")
    ):
        raise RuntimeError("Firefox .part file still exists; archive may be downloading")
    if archive.stat().st_size < 22 or not zipfile.is_zipfile(archive):
        raise ValueError("Archive missing ZIP central directory or incomplete")
    with zipfile.ZipFile(archive, "r") as z:
        checked=list(checked_members(z.infolist()))
        names=[i.filename for i in checked]
        classifications=[classify_entry(n) for n in names]
        selected=[]
        for i,kind in zip(checked,classifications):
            # A product is only a candidate if the exact target tile is in its path/name.
            if (target_tile in i.filename and kind["role_guess"] in ("DBM","DSM","DTM")
                    and PurePosixPath(i.filename).suffix.lower() in ALLOWED_EXTS):
                selected.append(i)
        compression=Counter(c["role_guess"] for c in classifications)
        format_counts=Counter(PurePosixPath(i.filename).suffix.lower() for i in checked)
        total=sum(i.file_size for i in checked)
        report={
            "archive":str(archive), "archive_bytes":archive.stat().st_size,
            "archive_sha256":None, "sha256_pending_full_pass":True,
            "member_count":len(checked), "uncompressed_total_bytes":total,
            "product_name_counts":dict(compression),
            "file_extension_counts":dict(format_counts),
            "target_tile":target_tile,
            "target_candidates":[{"name":i.filename,"bytes":i.file_size,
                "crc32":f"{i.CRC:08x}", **classify_entry(i.filename)} for i in selected],
            "source_assertion":"Names only; validate ASC header/CRS/vertical datum against official metadata before using",
            "safety":"ZIP paths, duplicates, symlinks, encryption and suspicious compression ratios checked",
        }
        inventory=[{"path":i.filename,"uncompressed_bytes":i.file_size,
                    "compressed_bytes":i.compress_size, "crc32":f"{i.CRC:08x}",
                    **kind} for i,kind in zip(checked,classifications)]
        # No output/partial extraction until all central-directory checks pass.
        if extract and not selected:
            raise ValueError("No verified names for selected LiDAR tile: nothing to extract")
        output.mkdir(parents=True)
        if extract:
            dest=output/"target_tile"
            for info in selected:
                # Avoid malicious or accidental re-use of internal paths.
                target=dest/str(PurePosixPath(info.filename))
                target.parent.mkdir(parents=True, exist_ok=True)
                # zipfile.open performs CRC verification while fully reading the member.
                with z.open(info) as source, target.open("xb") as sink:
                    shutil.copyfileobj(source, sink, length=1024*1024)
                if target.stat().st_size != info.file_size:
                    raise ValueError(f"Extracted file size mismatch: {target}")
                report.setdefault("extracted", []).append({
                    "path":str(target), "original_zip_path":info.filename,
                    "bytes":target.stat().st_size, "sha256":sha256(target)})
    (output/"manifest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (output/"inventory.json").write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({key:report[key] for key in
        ("archive_bytes","member_count","uncompressed_total_bytes",
         "product_name_counts","target_tile","target_candidates")},indent=2,ensure_ascii=False))
    print("Inventory:",output)
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--target-tile",default=DEFAULT_TILE)
    ap.add_argument("--extract-targets",action="store_true")
    args=ap.parse_args()
    inspect(args.archive,args.output,target_tile=args.target_tile,
            extract=args.extract_targets)


if __name__=="__main__":
    main()
