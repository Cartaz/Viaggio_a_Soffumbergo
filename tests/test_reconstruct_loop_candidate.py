"""Route candidate graph tests: never assert that connected OSM equals real drivable road."""
import unittest

from tools.reconstruct_loop_candidate import build


def sample():
    a, b, c = [13.35, 46.15], [13.3503, 46.15], [13.3503, 46.1503]
    network = {
        "type": "FeatureCollection",
        "route_status": "network_candidates_no_complete_loop_asserted",
        "features": [
            {"type": "Feature", "id": "way/1",
             "properties": {"highway": "residential"},
             "geometry": {"type": "LineString", "coordinates": [a, b, c, a]}}
        ]
    }
    prov = {"route_verified": False, "road_surface_height_status": "absent",
            "source_response_sha256": "test_hash", "osm_base_timestamp": "test"}
    anchors = {"START": tuple(a), "MID": tuple(b), "END": tuple(c)}
    sectors = (("A", ("START", "MID"), 25), ("F", ("MID", "END", "START"), 90))
    return network, prov, anchors, sectors


class LoopCandidateTests(unittest.TestCase):
    def test_closed_planar_only(self):
        network, prov, anchors, sectors = sample()
        result = build(network, prov, anchors=anchors, sectors=sectors)
        self.assertEqual([f["properties"]["sector"] for f in result["features"]], ["A", "F"])
        self.assertEqual(result["route_status"], "topologically_connected_candidate_not_a_verified_driving_route")
        self.assertFalse(result["usable_as_game_road"])
        self.assertIsNone(result["vertical_datum"])
        self.assertEqual(result["features"][0]["geometry"]["coordinates"][0],
                         result["features"][-1]["geometry"]["coordinates"][-1])
        self.assertTrue(all(len(pt) == 2 for feature in result["features"]
                            for pt in feature["geometry"]["coordinates"]))
        self.assertTrue(all(feature["properties"]["elevation_status"] == "unknown"
                            for feature in result["features"]))

    def test_reject_bad_snap_and_untrusted_metadata(self):
        network, prov, anchors, sectors = sample()
        far = dict(anchors)
        far["END"] = (14.0, 47.0)
        with self.assertRaises(ValueError):
            build(network, prov, anchors=far, sectors=sectors)
        with self.assertRaises(ValueError):
            build(network, dict(prov, route_verified=True), anchors=anchors, sectors=sectors)
        with self.assertRaises(ValueError):
            build(network, prov, max_snap_m=float("nan"), anchors=anchors, sectors=sectors)


if __name__ == "__main__":
    unittest.main()
