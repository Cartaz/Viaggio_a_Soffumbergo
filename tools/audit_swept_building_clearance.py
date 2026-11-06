"""CPU-only review of chassis motion between recorded native physics poses.

This is a *planimetric source-layout preflight*, not continuous native collision
detection. It interpolates sample centers linearly and bounds shortest-arc
rotation with a sagitta margin. Unsampled motion, roof elevation, and the
accuracy of OSM footprints remain unknown. Never change road/building assets.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
import shapely
from pyproj import Transformer, network


ROOT = Path(__file__).resolve().parents[1]
CHASSIS_CORNERS = np.asarray(
    [[x, y, z] for x in (-1.9, 1.9)
     for y in (-0.84, 0.84) for z in (0.325, 1.075)], dtype=float
)
CHASSIS_RADIUS_M = float(np.linalg.norm(CHASSIS_CORNERS, axis=1).max())
EPSILON_AREA_M2 = 1e-8


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def projected_chassis(centers: np.ndarray, quaternions: np.ndarray):
    """Reproduce the previous sampled chassis diagnostic, including mirrored Y."""
    xyz = quaternions[:, 1:] * np.asarray([-1., 1., -1.])
    w = quaternions[:, 0, None]
    local = CHASSIS_CORNERS[None]
    rotated = local + 2 * np.cross(
        xyz[:, None, :],
        np.cross(xyz[:, None, :], local) + w[:, :, None] * local
    )
    return shapely.convex_hull(shapely.multipoints((rotated + centers[:, None])[:, :, :2]))


def build_swept_envelopes(
    centers: np.ndarray,
    quaternions: np.ndarray,
    times: np.ndarray,
    *,
    max_interval_s: float = 0.2,
    max_step_m: float = 2.0,
    max_turn_deg: float = 25.0,
):
    """Construct projected convex endpoint sweeps with rotation interpolation pad.

    A rigid body's corner under linear center motion and shortest-arc rotation
    deviates by at most radius*(1-cos(delta/2)) from the straight chord.
    This bound is *conditional* on that interpolation; the actual unobserved
    physics trajectory is not known. Large discontinuities are left unchecked.
    """
    centers = np.asarray(centers, dtype=float)
    quaternions = np.asarray(quaternions, dtype=float)
    times = np.asarray(times, dtype=float)
    if centers.ndim != 2 or centers.shape[1] != 3 or len(centers) < 2:
        raise ValueError("At least two 3D chassis positions required")
    if quaternions.shape != (len(centers), 4) or times.shape != (len(centers),):
        raise ValueError("Invalid pose array dimensions")
    if not (np.isfinite(centers).all() and np.isfinite(quaternions).all() and np.isfinite(times).all()):
        raise ValueError("Non-finite telemetry")
    dt = np.diff(times)
    if np.any(dt <= 0):
        raise ValueError("Non-monotonic telemetry")
    norms = np.linalg.norm(quaternions, axis=1)
    if np.max(np.abs(norms-1)) > 1e-6:
        raise ValueError("Quaternions must be normalized")
    if max_interval_s <= 0 or max_step_m <= 0 or not 0 < max_turn_deg <= 180:
        raise ValueError("Invalid motion guard thresholds")

    step = np.linalg.norm(np.diff(centers[:, :2], axis=0), axis=1)
    cosine = np.clip(np.abs(np.sum(quaternions[:-1]*quaternions[1:], axis=1)), 0, 1)
    angle = 2 * np.arccos(cosine)
    valid = ((dt <= max_interval_s) & (step <= max_step_m)
             & (angle <= math.radians(max_turn_deg)))
    hulls = projected_chassis(centers, quaternions)
    swept = shapely.convex_hull(shapely.union(hulls[:-1], hulls[1:]))
    pad = CHASSIS_RADIUS_M * (1-np.cos(angle/2))
    return swept, pad, valid, dt, step, np.degrees(angle)


def candidate_intersections(
    sweeps: np.ndarray, padding: np.ndarray, valid: np.ndarray,
    buildings: np.ndarray,
):
    """Spatial-index broad phase then exact buffered planar area for candidates."""
    if len(sweeps) != len(padding) or len(sweeps) != len(valid):
        raise ValueError("Invalid segment arrays")
    accepted = np.flatnonzero(valid)
    if not len(accepted) or not len(buildings):
        return np.empty((2, 0), dtype=int), np.empty(0, dtype=float)
    bounds = shapely.bounds(sweeps[accepted])
    margin = padding[accepted] + 1e-7
    windows = shapely.box(
        bounds[:, 0]-margin, bounds[:, 1]-margin,
        bounds[:, 2]+margin, bounds[:, 3]+margin
    )
    tree = shapely.STRtree(buildings)
    hits = tree.query(windows, predicate="intersects")
    if not hits.shape[1]:
        return np.empty((2, 0), dtype=int), np.empty(0, dtype=float)
    segment = accepted[hits[0]]
    building = hits[1]
    enlarged = shapely.buffer(sweeps[segment], padding[segment] + 1e-7, quad_segs=8)
    overlap = shapely.area(shapely.intersection(enlarged, buildings[building]))
    positive = overlap > EPSILON_AREA_M2
    return np.stack([segment[positive], building[positive]]), overlap[positive]


def load_buildings(folder: Path, origin: np.ndarray):
    source = load_json(folder / "cover.geojson")
    response = load_json(folder / "response.json")
    relations = {int(f["id"].split("/")[1]) for f in source["features"]
                 if f["id"].startswith("relation/")}
    members = {
        member["ref"] for row in response["elements"]
        if row["type"] == "relation" and row["id"] in relations
        for member in row.get("members", [])
        if member["type"] == "way" and member.get("role", "") in ("", "outer", "inner")
    }
    network.set_network_enabled(False)
    projection = Transformer.from_crs(4326, 6708, always_xy=True, allow_ballpark=False)
    inverse = Transformer.from_crs(6708, 4326, always_xy=True, allow_ballpark=False)
    identifiers, buildings, rejected = [], [], []
    for feature in source["features"]:
        if feature["id"].startswith("way/") and int(feature["id"].split("/")[1]) in members:
            continue
        shape = shapely.from_geojson(json.dumps(feature["geometry"]))
        if shape.geom_type == "LineString" and shape.is_closed:
            shape = shapely.Polygon(shape.coords)
        shape = shapely.transform(shape, projection.transform, interleaved=False)
        shape = shapely.transform(
            shape, lambda p: np.c_[p[:, 0]-origin[0], origin[1]-p[:, 1]]
        )
        if not shape.is_valid:
            shape = shapely.make_valid(shape)
        if shape.geom_type not in ("Polygon", "MultiPolygon") or shape.is_empty:
            rejected.append(feature["id"])
            continue
        identifiers.append(feature["id"])
        buildings.append(shape)
    return identifiers, np.asarray(buildings, dtype=object), rejected, inverse


def load_telemetry(path: Path):
    data = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            data.append([float(row[key]) for key in
                         ("time_s", "x_m", "y_m", "z_m", "qw", "qx", "qy", "qz")])
    data = np.asarray(data, dtype=float)
    if data.shape[0] < 2 or data.shape[1] != 8:
        raise ValueError("Empty or incomplete native telemetry")
    return data[:, 0], data[:, 1:4]*[1, -1, 1], data[:, 4:8]


def run(prior_path: Path, output: Path, *, max_interval_s=0.2, max_step_m=2.0,
        max_turn_deg=25.0):
    if output.exists():
        raise FileExistsError("Never overwrite an existing diagnostic: " + str(output))
    prior = load_json(prior_path)
    if not prior.get("diagnostic_completed") or not prior.get("source_inputs_unchanged"):
        raise ValueError("Prior sampled diagnostic is not validated")
    paths = {Path(p): checksum for p, checksum in prior["protected_input_sha256"].items()}
    for path, expected in paths.items():
        if not path.is_file() or digest(path) != expected:
            raise ValueError("Protected source changed: " + str(path))
    prior_csv = prior_path.parent / "sampled_plan_overlaps.csv"
    if digest(prior_csv) != prior["overlap_csv_sha256"]:
        raise ValueError("Sampled evidence CSV changed")
    lap_path = Path(prior["native_full_lap_report"])
    lap = load_json(lap_path)
    if not (lap["full_lap_passed"] and lap["packaged"] and not lap["rendering"]):
        raise ValueError("Unsupported source lap")
    if lap["build_id"] != prior["build_id"]:
        raise ValueError("Build identity mismatch")
    draft = ROOT / "results/road_drafts" / prior["build_id"]
    pack = load_json(draft / "candidate_packaging_report.json")
    if pack["game_binary_sha256"] != prior["windows_binary_sha256"]:
        raise ValueError("Native executable identity mismatch")
    manifest = Path(load_json(draft / "import_report.json")["manifest"])
    world = load_json(manifest)
    if world["build_id"] != prior["build_id"]:
        raise ValueError("Manifest identity mismatch")
    origin = np.asarray(world["origin_ENH_m"], dtype=float)
    basename = lap_path.parent.name
    csv_path = lap_path.parent / (basename + ".csv")
    if csv_path not in paths:
        raise ValueError("Native lap CSV is not protected in prior report")
    times, positions, quaternions = load_telemetry(csv_path)
    if len(times) != prior["pose_samples_checked"]:
        raise ValueError("Sampled pose count changed")
    source = ROOT / "data/geography/world_cover_20261024_buildings_v4"
    source_ids, polygons, rejected, inverse = load_buildings(source, origin)
    if len(polygons) != prior["mapped_buildings_checked"]:
        raise ValueError("Building source count changed")
    if rejected != prior["unusable_geometries"]:
        raise ValueError("Building source interpretation changed")

    sweeps, padding, valid, dt, distance, turn = build_swept_envelopes(
        positions, quaternions, times,
        max_interval_s=max_interval_s,
        max_step_m=max_step_m, max_turn_deg=max_turn_deg
    )
    pairs, overlap = candidate_intersections(sweeps, padding, valid, polygons)
    cases = []
    for index in np.unique(pairs[1]):
        which = np.flatnonzero(pairs[1] == index)
        segments = pairs[0, which]
        peak_index = which[int(np.argmax(overlap[which]))]
        segment = int(pairs[0, peak_index])
        midpoint = (positions[segment] + positions[segment + 1])/2
        lon, lat = inverse.transform(midpoint[0]+origin[0], origin[1]-midpoint[1])
        cases.append({
            "source_id": source_ids[index],
            "positive_swept_intervals": int(len(which)),
            "maximum_interpolated_plan_overlap_m2": float(overlap[peak_index]),
            "first_time_s": float(times[segments.min()]),
            "last_time_s": float(times[segments.max()+1]),
            "peak_interval_s": [float(times[segment]), float(times[segment+1])],
            "peak_vehicle_center_wgs84": [lat, lon],
            "osm_url": "https://www.openstreetmap.org/" + source_ids[index],
            "streetview_or_survey_review_required": True,
            "real_building_collision_confirmed": False
        })
    cases.sort(key=lambda c: -c["maximum_interpolated_plan_overlap_m2"])
    sampled_ids = {row["source_id"] for row in prior["cases"]}
    swept_ids = {row["source_id"] for row in cases}
    before = {str(path): expected for path, expected in paths.items()}
    if not all(digest(path) == expected for path, expected in paths.items()):
        raise ValueError("Protected input mutated during the run")
    report = {
        "diagnostic_completed": True,
        "recorded_unix": time.time(),
        "build_id": prior["build_id"],
        "native_binary_sha256": prior["windows_binary_sha256"],
        "parent_sampled_report": str(prior_path),
        "parent_sampled_report_sha256": digest(prior_path),
        "pose_samples": int(len(times)),
        "total_pose_intervals": int(len(times)-1),
        "checked_intervals": int(np.count_nonzero(valid)),
        "skipped_intervals": int(np.count_nonzero(~valid)),
        "skipped_by_gap": int(np.count_nonzero(dt > max_interval_s)),
        "skipped_by_step": int(np.count_nonzero(distance > max_step_m)),
        "skipped_by_rotation": int(np.count_nonzero(turn > max_turn_deg)),
        "max_checked_time_gap_s": max_interval_s,
        "max_checked_translation_m": max_step_m,
        "max_checked_turn_deg": max_turn_deg,
        "candidate_mapped_buildings": int(len(polygons)),
        "swept_intervals_with_positive_area": int(len(np.unique(pairs[0]))),
        "mapped_buildings_with_swept_overlap": int(len(cases)),
        "sampled_building_ids": sorted(sampled_ids),
        "swept_building_ids": sorted(swept_ids),
        "new_building_ids_vs_samples": sorted(swept_ids-sampled_ids),
        "sampled_ids_missing_from_sweep": sorted(sampled_ids-swept_ids),
        "cases": cases,
        "source_input_sha256": before,
        "source_inputs_unchanged": True,
        "new_geometry_or_collision_created": False,
        "scope": "CPU-only planar envelope assuming linear position and shortest-arc "
                 "orientation interpolation between recorded native physics poses; "
                 "the sagitta pad bounds the interpolated corner arc, not arbitrary "
                 "unobserved motion. Discontinuities are explicitly skipped. This "
                 "does NOT verify actual 3D collisions, roofs, arcades, overhangs, "
                 "street alignment, or the accuracy of OSM building boundaries. "
                 "Building-source review in Street View is still necessary.",
        "osm_attribution": "© OpenStreetMap contributors (ODbL 1.0)"
    }
    output.mkdir(parents=True, exist_ok=False)
    overlaps_path = output / "swept_plan_overlaps.csv"
    with overlaps_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("segment_index", "time_from_s", "time_to_s",
                         "source_id", "swept_overlap_area_m2"))
        for segment, building, area in zip(pairs[0], pairs[1], overlap):
            writer.writerow((segment, times[segment], times[segment + 1],
                             source_ids[building], area))
    report["overlap_csv_sha256"] = digest(overlaps_path)
    (output / "report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({
        key: report[key] for key in (
            "build_id", "pose_samples", "total_pose_intervals", "checked_intervals",
            "skipped_intervals", "swept_intervals_with_positive_area",
            "mapped_buildings_with_swept_overlap", "new_building_ids_vs_samples",
            "sampled_ids_missing_from_sweep", "cases"
        )
    }, indent=2))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prior-report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--max-gap-s", type=float, default=0.2)
    p.add_argument("--max-step-m", type=float, default=2.0)
    p.add_argument("--max-turn-deg", type=float, default=25.0)
    a = p.parse_args()
    run(a.prior_report.resolve(), a.output.resolve(),
        max_interval_s=a.max_gap_s, max_step_m=a.max_step_m,
        max_turn_deg=a.max_turn_deg)


if __name__ == "__main__":
    main()
