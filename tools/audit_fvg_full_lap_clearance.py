"""Replay the full native Yaris lap against all available regional buildings.

Only local EPSG:6708 WFS snapshots around Mont Joanes are checked; other towns
are OUTSIDE THIS SURVEY. The result is projected 2D source comparison and cannot
prove either real-world collision or clearance of mast/crow's nest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from audit_swept_building_clearance import (
    build_swept_envelopes, candidate_intersections, digest, load_json,
    load_telemetry
)
from compare_fvg_building_footprints import to_unreal_shapes
from fetch_fvg_building_footprints import LAYERS, NATIVE_CRS

ROOT = Path(__file__).resolve().parents[1]


def segment_ranges(indices):
    values = np.unique(np.asarray(indices, dtype=int))
    if len(values) == 0:
        return []
    split = np.flatnonzero(np.diff(values) > 1) + 1
    return [[int(a[0]), int(a[-1])] for a in np.split(values, split)]


def summarize_hits(ids, pairs, areas, times, positions, origin, inverse):
    cases = []
    for building_index in np.unique(pairs[1]):
        hit_indices = np.flatnonzero(pairs[1] == building_index)
        segments = pairs[0, hit_indices]
        peak_ref = int(hit_indices[np.argmax(areas[hit_indices])])
        peak = int(pairs[0, peak_ref])
        center = (positions[peak] + positions[peak + 1]) / 2.
        lon, lat = inverse.transform(center[0]+origin[0], origin[1]-center[1])
        spans = segment_ranges(segments)
        cases.append({
            "regional_id": ids[int(building_index)],
            "intersecting_motion_intervals": len(segments),
            "max_interpolated_plan_overlap_m2": float(areas[peak_ref]),
            "first_time_s": float(times[int(segments.min())]),
            "last_time_s": float(times[int(segments.max())+1]),
            "peak_interval_s": [float(times[peak]), float(times[peak+1])],
            "approx_peak_wgs84_lat_lon": [float(lat), float(lon)],
            "interval_sequences": [
                [float(times[first]), float(times[last+1])]
                for first, last in spans
            ],
            "current_wall_collision_proven": False
        })
    return sorted(cases, key=lambda item: -item["max_interpolated_plan_overlap_m2"])


def audit(snapshot: Path, prior_path: Path, output: Path):
    if output.exists():
        raise FileExistsError("Do not overwrite any source audit")
    source = load_json(snapshot / "manifest.json")
    if source["native_crs"] != NATIVE_CRS or source["status"] != "complete":
        raise ValueError("Invalid WFS provenance or wrong CRS")
    prior = load_json(prior_path)
    if prior["build_id"] != "f4373a62b482" or not prior["source_inputs_unchanged"]:
        raise ValueError("Prior native telemetry not verified")
    for file, expected in prior["source_input_sha256"].items():
        if not Path(file).exists() or digest(Path(file)) != expected:
            raise ValueError("Protected source changed: " + file)
    sampled = load_json(Path(prior["parent_sampled_report"]))
    lap = Path(sampled["native_full_lap_report"])
    csv = lap.parent / (lap.parent.name + ".csv")
    times, centers, quats = load_telemetry(csv)
    if len(times) != prior["pose_samples"]:
        raise ValueError("Different native trace row count")

    manifest = Path(
        load_json(ROOT / "results/road_drafts/f4373a62b482/import_report.json")["manifest"]
    )
    build = load_json(manifest)
    origin = np.asarray(build["origin_ENH_m"], dtype=float)
    from pyproj import Transformer, network
    network.set_network_enabled(False)
    inverse = Transformer.from_crs(6708, 4326, always_xy=True, allow_ballpark=False)
    sweeps, padding, valid, dt, step, turn = build_swept_envelopes(centers, quats, times)
    if int(np.count_nonzero(valid)) != prior["checked_intervals"]:
        raise ValueError("Motion guard coverage changed")
    layer_results = {}
    fingerprints = {}
    for name in LAYERS:
        meta = source["layers"][name]
        file = snapshot / meta["filename"]
        raw = file.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        if sha != meta["sha256"]:
            raise ValueError("Regional WFS snapshot has changed")
        data = json.loads(raw)
        if not data.get("crs", {}).get("properties", {}).get("name", "").endswith("::6708"):
            raise ValueError("Regional WFS CRS mismatch")
        if len(data["features"]) != meta["features"]:
            raise ValueError("Regional WFS feature count changed")
        ids, shapes = to_unreal_shapes(data, origin)
        pairs, areas = candidate_intersections(sweeps, padding, valid, shapes)
        cases = summarize_hits(ids, pairs, areas, times, centers, origin, inverse)
        layer_results[name] = {
            "features_available_in_240m_wfs_bbox": len(ids),
            "motion_intervals_with_any_mapped_overlap": len(np.unique(pairs[0])),
            "regional_footprints_with_motion_overlap": len(cases),
            "total_positive_area_pairs": int(len(areas)),
            "max_case_area_m2": cases[0]["max_interpolated_plan_overlap_m2"] if cases else 0.,
            "cases": cases
        }
        fingerprints[str(file)] = sha
    if not all(digest(Path(file)) == sha for file, sha in fingerprints.items()):
        raise ValueError("One of the WFS snapshots changed during analysis")
    report = {
        "complete": True,
        "created_unix": time.time(),
        "native_build_id": prior["build_id"],
        "native_lap_report_sha256": digest(lap),
        "prior_swept_report_sha256": digest(prior_path),
        "regional_snapshot_manifest_sha256": digest(snapshot / "manifest.json"),
        "regional_bbox_e_n": source["native_bbox_e_n"],
        "regional_crs": NATIVE_CRS,
        "pose_samples": len(times),
        "total_motion_intervals": len(times)-1,
        "checked_intervals": int(np.count_nonzero(valid)),
        "skipped_intervals": int(np.count_nonzero(~valid)),
        "regional_layers": layer_results,
        "regional_snapshot_sha256": fingerprints,
        "native_assets_or_geometry_modified": False,
        "geographic_coverage_warning": "Only archived official building footprints in a 240m by 240m bbox around Mont Joanes; all other circuit areas have no official building data in this audit",
        "collision_warning": "2D planimetric interpolated chassis only, unverified walls, no elevations, no cabin accessories, no native collision or 4K simulation",
        "attribution": "Regione Autonoma Friuli Venezia Giulia, EDIFICI WFS; OSM contributors, ODbL"
    }
    output.mkdir(parents=True)
    (output / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "build": report["native_build_id"],
        "checked_intervals": report["checked_intervals"],
        "regional_results": {
            k: {x:v for x,v in result.items() if x != "cases"}
               | {"top_5": result["cases"][:5]}
            for k,result in layer_results.items()
        },
        "output": str(output)
    }, indent=2, ensure_ascii=False))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", type=Path, required=True)
    p.add_argument("--swept-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    audit(args.snapshot.resolve(), args.swept_report.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
