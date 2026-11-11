"""Evaluate vertical LiDAR evidence at *actual* chassis/footprint overlap areas.

Unlike center-point sampling, this intersects the original native f437 swept
vehicle footprints with independent regional/OSM building outlines. Each
overlap is sampled on the native 0.5m DTM/DBM/DSM grid as a weighted union of
intersected raster cells. It is evidence of mapped surface elevations only,
NOT a 3D wall collision or proof of full game safety.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np
import shapely
from pyproj import Transformer, network

from audit_mont_joanes_height_sources import (
    file_hash, inspect_optional_manifest, parse_ascii_header
)
from audit_swept_building_clearance import (
    build_swept_envelopes, load_json, load_telemetry
)
from fetch_fvg_building_footprints import LAYERS
from review_mont_joanes_clearance import TARGETS
ROOT=Path(__file__).resolve().parents[1]
ROLES=("DTM","DBM","DSM_FIRST","DSM_LAST")


def read_aligned_rasters(dtm_path: Path, source_manifest: Path):
    """Read only validated source products, refuse even half-cell misalignment."""
    dtm = parse_ascii_header(dtm_path)
    provenance = json.loads(source_manifest.read_text(encoding="utf-8"))
    if provenance.get("original_dtm_sha256") and file_hash(dtm_path) != provenance["original_dtm_sha256"]:
        raise ValueError("DTM SHA-256 differs from original Eagle source match")
    additional = inspect_optional_manifest(source_manifest)
    if set(additional) != {"DBM", "DSM_FIRST", "DSM_LAST"}:
        raise ValueError("This audit needs DBM and both DSM returns, all ellipsoidal")
    layout = (dtm.rows,dtm.cols,dtm.x_center,dtm.y_center,dtm.cell)
    grids={"DTM":dtm}
    for name,(grid,digest) in additional.items():
        if (grid.rows,grid.cols,grid.x_center,grid.y_center,grid.cell) != layout:
            raise ValueError(f"Source raster not aligned with original DTM: {name}")
        grids[name]=grid
    data={}
    for role in ROLES:
        grid=grids[role]
        values=np.loadtxt(grid.path,skiprows=6,dtype=np.float32,ndmin=2)
        if values.shape!=(dtm.rows,dtm.cols):
            raise ValueError("Raster rows/columns do not match header")
        values[~np.isfinite(values)]=np.nan
        values[np.isclose(values,grid.nodata)]=np.nan
        data[role]=values
    return dtm,data, {name:file_hash(g.path) for name,g in grids.items()}


def weighted_surface_summary(region, grid, arrays):
    """Use area of each intersected 0.5m cell, never just centroid pixels."""
    if region.is_empty or region.area<=0:
        return {"intersected_map_area_m2":0.0,"covered_raster_area_m2":0.0,
                "cells_touching_region":0,"valid_cells":0,
                "DBM":None,"DSM_FIRST":None,"DSM_LAST":None}
    x0,y0,x1,y1=region.bounds
    c=grid.cell
    start_x=max(0,int(np.floor((x0-grid.x_center+c/2)/c)))
    stop_x=min(grid.cols-1,int(np.floor((x1-grid.x_center+c/2)/c)))
    start_y=max(0,int(np.floor((y0-grid.y_center+c/2)/c)))
    stop_y=min(grid.rows-1,int(np.floor((y1-grid.y_center+c/2)/c)))
    values={k:[] for k in ("DBM","DSM_FIRST","DSM_LAST")}
    covered=0.
    touched=0
    valid_count=0
    for iy in range(start_y,stop_y+1):
        n=grid.y_center+iy*c
        row=grid.rows-1-iy
        for ix in range(start_x,stop_x+1):
            e=grid.x_center+ix*c
            area=float(shapely.area(shapely.intersection(
                region,shapely.box(e-c/2,n-c/2,e+c/2,n+c/2))))
            if area<=1e-9:
                continue
            touched+=1
            dtm=float(arrays["DTM"][row,ix])
            if not np.isfinite(dtm):
                continue
            valid_count+=1
            for role in values:
                measured=float(arrays[role][row,ix])
                if np.isfinite(measured):
                    values[role].append((area,measured-dtm))
            covered+=area
    summary={"intersected_map_area_m2":float(region.area),
             "covered_raster_area_m2":covered,
             "cells_touching_region":touched,"valid_cells":valid_count}
    for role,measurements in values.items():
        if not measurements:
            summary[role]=None
            continue
        w=np.asarray([v[0] for v in measurements])
        dz=np.asarray([v[1] for v in measurements])
        total=float(w.sum())
        summary[role]={
            "area_m2":total,
            "min_delta_m":float(dz.min()),
            "mean_delta_m":float(np.average(dz,weights=w)),
            "max_delta_m":float(dz.max()),
            "fraction_of_valid_area_above_0_5m":float(w[dz>0.5].sum()/total),
            "fraction_of_valid_area_above_1_5m":float(w[dz>1.5].sum()/total),
            "area_above_0_5m_m2":float(w[dz>0.5].sum()),
            "area_above_1_5m_m2":float(w[dz>1.5].sum()),
            "weighted_height_is_surveyed_wall":False
        }
    return summary


def to_native_utm(shapes, origin):
    return shapely.transform(shapes,lambda x:np.c_[x[:,0]+origin[0],origin[1]-x[:,1]])


def case_intervals(case,times, *, is_fvg):
    if is_fvg:
        windows=case["interval_sequences"]
    else:
        windows=[[case["first_time_s"],case["last_time_s"]]]
    ids=[]
    for start,end in windows:
        a=int(np.searchsorted(times,start,side="left"))
        b=int(np.searchsorted(times,end,side="left"))
        if a>=len(times) or b>=len(times) or abs(times[a]-start)>0.001 or abs(times[b]-end)>0.001:
            raise ValueError("Native interval endpoints not reproducible")
        ids.extend(range(a,b))
    return sorted(set(ids))


def analyze(regional_report: Path, osm_report:Path, snapshot:Path,
            manifest_path:Path, dtm_path:Path, output:Path):
    if output.exists():
        raise FileExistsError("Do not overwrite existing vertical conflict audit")
    reg=load_json(regional_report); osm=load_json(osm_report)
    if (reg["native_build_id"]!="f4373a62b482" or
        osm["build_id"]!="f4373a62b482" or not reg["complete"] or not osm["diagnostic_completed"]):
        raise ValueError("This tool requires original verified f437 native evidence")
    grid,rasters,hashes=read_aligned_rasters(dtm_path,manifest_path)
    src=load_json(snapshot/"manifest.json")
    fvg_raw=snapshot/src["layers"]["DBS_EDIFICATO"]["filename"]
    if file_hash(fvg_raw)!=src["layers"]["DBS_EDIFICATO"]["sha256"]:
        raise ValueError("Regional building map was modified")
    shapes_reg={f["id"]:shapely.force_2d(shapely.from_geojson(json.dumps(f["geometry"])))
                for f in load_json(fvg_raw)["features"]}
    from pyproj import Transformer
    network.set_network_enabled(False)
    project=Transformer.from_crs(4326,6708,always_xy=True,allow_ballpark=False)
    osm_raw=load_json(ROOT/"data/geography/world_cover_20261024_buildings_v4/cover.geojson")
    shapes_osm={}
    for f in osm_raw["features"]:
        if f["id"] not in TARGETS:
            continue
        geom=shapely.from_geojson(json.dumps(f["geometry"]))
        if geom.geom_type=="LineString" and geom.is_closed:
            geom=shapely.Polygon(geom)
        shapes_osm[f["id"]]=shapely.transform(
            geom,project.transform,interleaved=False)
    if set(shapes_osm)!=set(TARGETS):
        raise ValueError("Missing archived OSM target")
    native_manifest=load_json(Path(load_json(
        ROOT/"results/road_drafts/f4373a62b482/import_report.json")["manifest"]))
    origin=np.asarray(native_manifest["origin_ENH_m"],dtype=float)
    prior=load_json(Path(osm["parent_sampled_report"]))
    lap=Path(prior["native_full_lap_report"])
    telemetry=lap.parent/(lap.parent.name+".csv")
    times,centers,quats=load_telemetry(telemetry)
    if len(times)!=osm["pose_samples"]:
        raise ValueError("Native CSV was replaced")
    cases=[]
    collection=[]
    for case in reg["regional_layers"]["DBS_EDIFICATO"]["cases"]:
        fid=case["regional_id"]
        if fid not in shapes_reg:
            raise ValueError("DBTsped mapped building not in official snapshot")
        collection.append((fid,shapes_reg[fid],case,True))
    for case in osm["cases"]:
        fid=case["source_id"]
        if fid in shapes_osm:
            collection.append((fid,shapes_osm[fid],case,False))
    for fid,building,case,is_fvg in collection:
        segments=case_intervals(case,times,is_fvg=is_fvg)
        geometries=[]
        max_area=-1.
        max_interval=None
        for index in segments:
            if index+1>=len(times):
                raise ValueError("Pose index outside native lap")
            hull,margin,valid,*_=build_swept_envelopes(
                centers[index:index+2],quats[index:index+2],times[index:index+2])
            if not valid[0]:
                raise ValueError("Discontinuous native pose, cannot interpolate")
            chassis=shapely.buffer(hull[0],float(margin[0])+1e-7,quad_segs=8)
            overlap=shapely.intersection(to_native_utm(chassis,origin),building)
            if overlap.area>1e-9:
                geometries.append(overlap)
                if overlap.area>max_area:
                    max_area=float(overlap.area)
                    max_interval=[float(times[index]),float(times[index+1])]
                    peak_overlap=overlap
        if not geometries:
            raise ValueError(f"No original planar overlap reproduced for {fid}")
        prior_peak=case["max_interpolated_plan_overlap_m2"] if is_fvg else case["maximum_interpolated_plan_overlap_m2"]
        if abs(max_area-prior_peak)>0.00002:
            raise ValueError(f"Native chassis/footprint mismatch {fid}: {max_area} vs {prior_peak}")
        combined=shapely.union_all(geometries)
        cases.append({
            "source_id":fid,
            "source_layer":"DBTsped FVG 2017–2020" if is_fvg else "OSM 2026",
            "positive_motion_intervals":len(geometries),
            "peak_interval_s":max_interval,
            "peak_overlap_m2":max_area,
            "unique_intersection_footprint_area_m2":float(combined.area),
            "peak_surface_evidence":weighted_surface_summary(peak_overlap,grid,rasters),
            "union_surface_evidence":weighted_surface_summary(combined,grid,rasters),
            "real_ground_wall_at_contact_verified":False
        })
    if not cases:
        raise ValueError("No geometry cases available")
    expected={name:file_hash(Path(entry["path"])) for name,entry in
              load_json(manifest_path)["products"].items()}
    if any(expected.get(name)!=hashes[name] for name in expected):
        raise ValueError("LiDAR product changed during analysis")
    result={
        "completed":True,"case_count":len(cases),"candidate_build":"f4373a62b482",
        "created_unix":time.time(),
        "sweep_report_sha256":file_hash(osm_report),
        "regional_report_sha256":file_hash(regional_report),
        "source_manifest_sha256":file_hash(manifest_path),
        "raster_sha256":hashes,
        "source_regional_geojson_sha256":file_hash(fvg_raw),
        "source_archive":"Eagle.fvg LiDAR RAFVG 2017–2020, 0.5m, ellipsoidal RDN2008/TM33",
        "raster_crs":"EPSG:6708",
        "cases":cases,
        "game_geometry_modified":False,
        "not_a_native_3d_collision_test":True,
        "limitations":"Surface height relative to ground in 0.5m raster cells covering geometrical 2D intersection of mapped footprint and swept chassis; it is not a measured real wall, vertical collision volume, head/crow nest clearance or certification of driveability."
    }
    output.mkdir(parents=True)
    (output/"report.json").write_text(
        json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({"output":str(output),"cases":[{
        "source":c["source_id"],
        "positive_intervals":c["positive_motion_intervals"],
        "peak_m2":round(c["peak_overlap_m2"],4),
        "union_m2":round(c["unique_intersection_footprint_area_m2"],4),
        "DBM_peak":c["peak_surface_evidence"]["DBM"],
        "DBM_union":c["union_surface_evidence"]["DBM"]
    } for c in cases]},ensure_ascii=False,indent=2))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--regional-report",type=Path,default=ROOT/"results/fvg_official_buildings/full_lap_20261107_v1/report.json")
    p.add_argument("--osm-report",type=Path,default=ROOT/"results/building_context/f437_swept_chassis_20261106_v1/report.json")
    p.add_argument("--snapshot",type=Path,default=ROOT/"results/fvg_official_buildings/mont_joanes_20261107_v1")
    p.add_argument("--height-manifest",type=Path,required=True)
    p.add_argument("--dtm",type=Path,default=ROOT/"data/lidar/raw_20261020/Ell_DTM_06701307.asc")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    analyze(a.regional_report.resolve(),a.osm_report.resolve(),a.snapshot.resolve(),
            a.height_manifest.resolve(),a.dtm.resolve(),a.output.resolve())


if __name__=="__main__":
    main()
