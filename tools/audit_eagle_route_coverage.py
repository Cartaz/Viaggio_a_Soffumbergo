"""Verify all native f437 driving poses are covered by original DTM and Eagle surfaces.

Uses the 41-tile verified manifest and the previously recorded 105k native
poses. Reports both geographic tile coverage and nearest-cell NoData validity.
This does not establish collision safety or validate the current 4K package.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np
from pyproj import Transformer,network

from audit_mont_joanes_height_sources import parse_ascii_header,file_hash
from audit_swept_building_clearance import load_json,load_telemetry

ROOT=Path(__file__).resolve().parents[1]
ROLES=("DTM","DBM","DSM_FIRST","DSM_LAST")


def map_points_to_tiles(east,north,tiles):
    """Return first containing original raster tile and its cell coordinates."""
    n=len(east)
    assigned=np.full(n,-1,dtype=np.int32)
    indices={}
    for it,(tile,grid) in enumerate(tiles):
        selection=(assigned<0)&(east>=grid.x_center)&(
            east<=grid.x_center+(grid.cols-1)*grid.cell)&(
            north>=grid.y_center)&(north<=grid.y_center+(grid.rows-1)*grid.cell)
        assigned[selection]=it
        indices[tile]=np.flatnonzero(selection)
    return assigned,indices


def nearest_validity(grid,arrays, east,north):
    """Fast nearest-cell availability for an already georeferenced LiDAR grid."""
    if not len(east):
        return {r:np.zeros(0,dtype=bool) for r in ROLES}
    col=np.rint((east-grid.x_center)/grid.cell).astype(np.int32)
    north_row=np.rint((north-grid.y_center)/grid.cell).astype(np.int32)
    if not ((0<=col).all() and (col<grid.cols).all() and (0<=north_row).all() and (north_row<grid.rows).all()):
        raise ValueError("Point assigned beyond raster center limits")
    row=grid.rows-1-north_row
    return {role: np.isfinite(arrays[role][row,col]) & (
        ~np.isclose(arrays[role][row,col],grid.nodata))
            for role in ROLES}


def audit(tile_manifest:Path, output:Path):
    if output.exists():
        raise FileExistsError("Preserve existing route coverage audit")
    source=load_json(tile_manifest)
    if (source["status"]!="complete" or source["horizontal_crs"]!="EPSG:6708"
        or source["vertical_datum"]!="ellipsoidal" or len(source["tiles"])!=source["route_tile_count"]):
        raise ValueError("Invalid Eagle route surface provenance")
    native=load_json(ROOT/"results/building_context/f437_swept_chassis_20261106_v1/report.json")
    if native["build_id"]!="f4373a62b482" or not native["diagnostic_completed"]:
        raise ValueError("Unsupported native build")
    sampled=load_json(Path(native["parent_sampled_report"]))
    native_lap=Path(sampled["native_full_lap_report"])
    csv=native_lap.parent/(native_lap.parent.name+".csv")
    times,positions,quats=load_telemetry(csv)
    if len(times)!=native["pose_samples"]:
        raise ValueError("Not the original full native lap")
    road=load_json(Path(load_json(ROOT/"results/road_drafts/f4373a62b482/import_report.json")["manifest"]))
    origin=np.asarray(road["origin_ENH_m"],float)
    east=positions[:,0]+origin[0]
    north=origin[1]-positions[:,1]
    tiles=[]
    for tile,row in sorted(source["tiles"].items()):
        dtm=Path(row["original_dtm"]["path"])
        if file_hash(dtm)!=row["original_dtm"]["sha256"]:
            raise ValueError("Original route DTM mutated: "+tile)
        hdr=parse_ascii_header(dtm)
        tiles.append((tile,hdr))
    assigned,groups=map_points_to_tiles(east,north,tiles)
    by_role={role:np.zeros(len(times),dtype=bool) for role in ROLES}
    per_tile=[]
    dataset_dir=tile_manifest.parent
    for tile,header in tiles:
        selection=groups[tile]
        row=source["tiles"][tile]
        arrays={}
        for role in ROLES:
            if role=="DTM":
                file=header.path
            else:
                data=row["products"][role]
                file=dataset_dir/data["relative_path"]
                if not file.is_file() or file_hash(file)!=data["sha256"]:
                    raise ValueError("Changed raster: "+str(file))
                other=parse_ascii_header(file)
                if ((other.rows,other.cols,other.x_center,other.y_center,other.cell)!=
                    (header.rows,header.cols,header.x_center,header.y_center,header.cell)):
                    raise ValueError("Raster grid mismatch: "+str(file))
            values=np.loadtxt(file,skiprows=6,dtype=np.float32,ndmin=2)
            if values.shape!=(header.rows,header.cols):
                raise ValueError("Data dimensions != raster header")
            arrays[role]=values
        valid=nearest_validity(header,arrays,east[selection],north[selection])
        for role in ROLES:
            by_role[role][selection]=valid[role]
        per_tile.append({
            "tile":tile,
            "sampled_native_poses":int(len(selection)),
            "valid_cells_for_all_roles":int(np.count_nonzero(
                np.logical_and.reduce(list(valid.values())))) if len(selection) else 0,
            "valid_by_role":{role:int(np.count_nonzero(flag)) for role,flag in valid.items()}
        })
        if len(selection):
            print(f"CHECKED {tile}: {len(selection)} poses, all roles valid "
                  f"{per_tile[-1]['valid_cells_for_all_roles']}",flush=True)
    network.set_network_enabled(False)
    inverse=Transformer.from_crs(6708,4326,always_xy=True,allow_ballpark=False)
    uncovered=np.flatnonzero(assigned<0)
    all_valid=np.logical_and.reduce(list(by_role.values()))
    broken=np.flatnonzero((assigned>=0)&(~all_valid))
    def samples(indices):
        a=[]
        for i in indices[:30]:
            lon,lat=inverse.transform(float(east[i]),float(north[i]))
            a.append({"native_pose_index":int(i),"time_s":float(times[i]),
                      "latitude":float(lat),"longitude":float(lon),
                      "native_e_m":float(east[i]),"native_n_m":float(north[i])})
        return a
    report={
        "complete":True,"candidate_build":"f4373a62b482",
        "created_unix":time.time(),
        "source_manifest_sha256":file_hash(tile_manifest),
        "source_native_telemetry_sha256":file_hash(csv),
        "sample_count":len(times),"surface_tile_count":len(tiles),
        "geographically_covered_pose_count":int(np.count_nonzero(assigned>=0)),
        "uncovered_pose_count":int(len(uncovered)),
        "valid_pose_count_all_four_products":int(np.count_nonzero(all_valid)),
        "invalid_surface_pose_count":int(len(broken)),
        "valid_by_role":{role:int(np.count_nonzero(arr)) for role,arr in by_role.items()},
        "uncovered_pose_examples":samples(uncovered),
        "nodata_pose_examples":samples(broken),
        "per_tile":per_tile,
        "no_native_game_assets_modified":True,
        "not_a_wall_collision_test":True,
        "note":"Nearest 0.5m raster cell at each authentic native vehicle center; this verifies source coverage, not 3D geometry at vehicle corners or LiDAR source accuracy."
    }
    output.mkdir(parents=True)
    (output/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:report[k] for k in
        ("sample_count","surface_tile_count","geographically_covered_pose_count",
         "uncovered_pose_count","valid_pose_count_all_four_products",
         "invalid_surface_pose_count","valid_by_role")},ensure_ascii=False,indent=2))
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tile-manifest",type=Path,default=ROOT/"results/eagle_bundle/ellipsoid_route_20261111_v1/manifest.json")
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    audit(a.tile_manifest.resolve(),a.output.resolve())


if __name__=="__main__":
    main()
