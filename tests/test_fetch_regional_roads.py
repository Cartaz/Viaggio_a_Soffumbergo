"""Regional OSM acquisition tests (no network and no real-route claims)."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.fetch_regional_roads import acquire, normalize_regional


def raw_network():
    nodes = [
        {"type": "node", "id": 1, "lon": 13.35, "lat": 46.15},
        {"type": "node", "id": 2, "lon": 13.36, "lat": 46.15},
        {"type": "node", "id": 3, "lon": 13.37, "lat": 46.15},
    ]
    ways = [
        {"type": "way", "id": 20, "nodes": [1, 2],
         "tags": {"highway": "residential", "name": "fictional test road"}},
        {"type": "way", "id": 21, "nodes": [2, 3],
         "tags": {"highway": "service", "access": "private"}},
        {"type": "way", "id": 22, "nodes": [1, 3],
         "tags": {"highway": "footway"}},
    ]
    return {"elements": nodes + ways,
            "osm3s": {"timestamp_osm_base": "2026-10-01T00:00:00Z"}}


class RegionalRoadsTests(unittest.TestCase):
    def test_network_only_with_license_and_access_flags(self):
        with tempfile.TemporaryDirectory() as folder:
            raw = json.dumps(raw_network()).encode("utf-8")
            report = acquire(raw, folder)
            self.assertEqual(report["feature_count"], 3)
            self.assertEqual(report["possible_motor_road_candidates"], 1)
            self.assertFalse(report["route_verified"])
            self.assertIsNone(report["downloaded_utc"])
            output = json.loads((Path(folder) / "regional_roads.geojson").read_text())
            self.assertEqual(output["route_status"], "network_candidates_no_complete_loop_asserted")
            by_id = {f["id"]: f for f in output["features"]}
            self.assertTrue(by_id["way/20"]["properties"]["possible_motor_road_candidate"])
            self.assertFalse(by_id["way/21"]["properties"]["possible_motor_road_candidate"])
            self.assertFalse(by_id["way/22"]["properties"]["possible_motor_road_candidate"])
            self.assertEqual(len(by_id["way/20"]["geometry"]["coordinates"][0]), 2)

    def test_bad_payload_cannot_replace_good_output(self):
        with tempfile.TemporaryDirectory() as folder:
            acquire(json.dumps(raw_network()).encode("utf-8"), folder)
            previous = (Path(folder) / "regional_roads.geojson").read_bytes()
            missing_node = raw_network()
            missing_node["elements"] = [e for e in missing_node["elements"]
                                         if not (e["type"] == "node" and e["id"] == 2)]
            with self.assertRaises(ValueError):
                acquire(json.dumps(missing_node).encode("utf-8"), folder)
            with self.assertRaisesRegex(ValueError, "Overpass error"):
                acquire(b'{"remark":"timeout", "elements":[]}', folder)
            self.assertEqual(previous, (Path(folder) / "regional_roads.geojson").read_bytes())

    def test_reject_missing_roads(self):
        with self.assertRaisesRegex(ValueError, "no road ways"):
            normalize_regional({"elements": [{"type": "node", "id": 1, "lat": 46.15,
                                               "lon": 13.35}]}, "test", "fake")


if __name__ == "__main__":
    unittest.main()
