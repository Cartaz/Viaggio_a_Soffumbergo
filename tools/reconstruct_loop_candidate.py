#!/usr/bin/env python3
"""Reconstruct REVIEW-ONLY 2D OSM route candidates for the user's exact circuit.

No terrain heights, widths, driving legality, or verified turn restrictions.
The network must originate from fetch_regional_roads.py, not Google geometry.
"""
import argparse
import json
import math
from pathlib import Path

from extract_sector_b import highway_graph, nearest_node, shortest_path

ROOT = Path(__file__).resolve().parents[1]
ANCHORS = {
    "START": (13.3465502, 46.1527301),
    "CIR-02": (13.3456331, 46.1524578),
    "CIR-03": (13.3621382, 46.1285473),
    "CIR-04": (13.3624209, 46.1294583),
    "CIR-05": (13.3623277, 46.1287162),
    "CIR-06": (13.3666683, 46.1271692),
    "CIR-07": (13.3820732, 46.1331275),
    "CIR-08": (13.3838913, 46.1345686),
    "CIR-09": (13.3913328, 46.1369502),
    "V-START": (13.3924178, 46.1590017),
    "V-PIAZZA": (13.3933009, 46.1569279),
    "CIR-12": (13.379205, 46.1580732),
    "CIR-13": (13.3623302, 46.1676159),
    "CIR-14": (13.3596292, 46.1659437),
    "CANAL": (13.3592542, 46.1657647),
    "CIR-17": (13.3578603, 46.1632064),
    "CIR-18": (13.3528119, 46.1588268),
    "CIR-19": (13.346199, 46.1527672),
}
# Google Maps instruction distances are rounded and COMPARISON ONLY.
SECTORS = (
    ("A", ("START", "CIR-02", "CIR-03", "CIR-04", "CIR-05", "CIR-06"), 4009),
    ("B", ("CIR-06", "CIR-07", "CIR-08"), 2020),
    ("C", ("CIR-08", "CIR-09", "V-START"), 4300),
    ("V", ("V-START", "V-PIAZZA", "V-START"), 530),
    ("D", ("V-START", "CIR-12"), 1400),
    ("E", ("CIR-12", "CIR-13", "CIR-14", "CANAL"), 4563),
    ("F", ("CANAL", "CIR-17", "CIR-18", "CIR-19", "START"), 1872),
)


def build(network, provenance, max_snap_m=40.0, anchors=ANCHORS, sectors=SECTORS):
    if max_snap_m <= 0 or not math.isfinite(max_snap_m):
        raise ValueError("Invalid snap tolerance")
    if (network.get("route_status") != "network_candidates_no_complete_loop_asserted" or
            provenance.get("route_verified") is not False or
            provenance.get("road_surface_height_status") != "absent"):
        raise ValueError("Expected the provenance-preserving, heightless regional OSM dataset")
    graph = highway_graph(network)
    snapped = {key: nearest_node(graph, position, max_snap_m) for key, position in anchors.items()}
    features, previous_end = [], None
    for sector, refs, app_m in sectors:
        combined, meters = [], 0.0
        for a, b in zip(refs, refs[1:]):
            leg, length = shortest_path(graph, snapped[a][0], snapped[b][0])
            combined.extend(leg[1:] if combined else leg)
            meters += length
        if len(combined) < 2:
            raise ValueError("Empty segment: " + sector)
        if previous_end is not None and combined[0] != previous_end:
            raise ValueError("Disconnected sector boundary " + sector)
        previous_end = combined[-1]
        delta = round(meters - app_m, 1)
        props = {
            "sector": sector,
            "candidate_status": "OSM_2D_shortest_path_requires_original_itinerary_review",
            "original_anchor_ids": list(refs),
            "snap_distances_m": [round(snapped[r][1], 1) for r in refs],
            "length_osm_horizontal_m_approx": round(meters, 1),
            "google_instruction_rounded_distance_m": app_m,
            "difference_from_rounded_instructions_m": delta,
            "length_similar_not_alignment_verified": abs(delta) <= max(200, app_m * 0.07),
            "osm_base_timestamp": provenance.get("osm_base_timestamp"),
            "osm_source_response_sha256": provenance.get("source_response_sha256"),
            "vertical_datum": None, "elevation_status": "unknown",
            "width_m": None, "crossfall_status": "unknown",
            "one_way_and_turn_restrictions_checked": False,
            "driver_legality_checked": False, "streetview_continuity_checked": False,
            "ready_for_road_mesh": False
        }
        features.append({"type": "Feature", "id": "OSM-REVIEW-" + sector,
                         "geometry": {"type": "LineString", "coordinates": [list(c) for c in combined]},
                         "properties": props})
    if features[-1]["geometry"]["coordinates"][-1] != features[0]["geometry"]["coordinates"][0]:
        raise ValueError("The graph-based candidate does not close")
    return {
        "type": "FeatureCollection",
        "name": "Circuito_Soffumbergo_OSM_planimetric_review_ONLY",
        "coordinate_reference": "EPSG:4326 lon lat, NO Z",
        "route_status": "topologically_connected_candidate_not_a_verified_driving_route",
        "license": "© OpenStreetMap contributors, ODbL 1.0",
        "source_regional_osm_sha256": provenance.get("source_response_sha256"),
        "length_2d_total_m_approx": round(sum(f["properties"]["length_osm_horizontal_m_approx"] for f in features), 1),
        "maps_route_total_km_rounded": 18.7,
        "vertical_datum": None,
        "usable_as_game_road": False,
        "features": features,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--provenance", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--max-snap-m", type=float, default=40.0)
    args = ap.parse_args()
    result = build(json.loads(args.input.read_text(encoding="utf-8")),
                   json.loads(args.provenance.read_text(encoding="utf-8")),
                   args.max_snap_m)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for f in result["features"]:
        p = f["properties"]
        print(f"{p['sector']}: {p['length_osm_horizontal_m_approx']} m "
              f"(Maps directions ~{p['google_instruction_rounded_distance_m']} m); "
              f"length similarity: {p['length_similar_not_alignment_verified']}")
    print(f"Candidate loop only: {result['length_2d_total_m_approx']} m, 2D, no verified road surface")


if __name__ == "__main__":
    main()
