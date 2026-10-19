"""Check sector V source geometry, exact reversal, attribution and separation of unverified features."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "data" / "geography"
ROADS = ["way/1041538032", "way/136283440", "way/136494659", "way/1107817252"]


class SectorVTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = {f["id"]: f for f in json.loads((GEO / "osm_survey.geojson").read_text(encoding="utf-8"))["features"]}
        cls.route = json.loads((GEO / "sector_v_route.geojson").read_text(encoding="utf-8"))
        cls.context = json.loads((GEO / "sector_v_context.geojson").read_text(encoding="utf-8"))
        cls.survey = json.loads((GEO / "sector_v_survey.json").read_text(encoding="utf-8"))

    def test_expected_ways_and_exact_reversal(self):
        parts = [self.source[k]["geometry"]["coordinates"] for k in ROADS]
        for first, second in zip(parts, parts[1:]):
            self.assertEqual(first[-1], second[0])
        expected = list(parts[0])
        for part in parts[1:]:
            expected += part[1:]
        a, b = self.route["features"][:2]
        self.assertEqual(a["geometry"]["coordinates"], expected)
        self.assertEqual(b["geometry"]["coordinates"], expected[::-1])
        self.assertEqual(a["properties"]["osm_way_ids"], ROADS)
        self.assertEqual(b["properties"]["osm_way_ids"], ROADS[::-1])

    def test_maneuvers_and_boundaries(self):
        maneuvers = self.survey["maneuvers"]
        self.assertEqual([s["step"] for s in maneuvers], [11, 12, 13, 14])
        self.assertEqual(sum(s["distance_m_app_rounded"] for s in maneuvers), 530)
        self.assertEqual(maneuvers[0]["osm_way_ids"], ROADS[:2])
        self.assertEqual(maneuvers[3]["osm_way_ids"], ROADS[:2][::-1])
        self.assertEqual(self.survey["handoff_to_sector_d"]["next_step"], 15)
        self.assertEqual(self.survey["anchors"]["start_wgs84"], self.route["features"][0]["geometry"]["coordinates"][0])
        self.assertEqual(self.survey["anchors"]["piazza_road_wgs84"], self.route["features"][0]["geometry"]["coordinates"][-1])

    def test_2d_source_unchanged_and_footways_outside_driving_route(self):
        context = {f["id"]: f for f in self.context["features"] if f["id"].startswith("way/")}
        for f in self.context["features"]:
            if f["id"].startswith("way/"):
                self.assertEqual(f["geometry"], self.source[f["id"]]["geometry"])
        self.assertEqual(len([f for f in self.context["features"] if f["properties"].get("map_use") == "cartographic_footprint_not_verified_facade"]), 53)
        self.assertIn("way/36686356", context)
        self.assertEqual(context["way/243981581"]["properties"]["highway"], "steps")
        self.assertEqual(context["way/604025801"]["properties"]["tunnel"], "building_passage")
        self.assertNotIn("way/243981581", self.route["features"][0]["properties"]["osm_way_ids"])
        for f in self.route["features"]:
            if f["geometry"]["type"] == "LineString":
                self.assertTrue(all(len(p) == 2 for p in f["geometry"]["coordinates"]))

    def test_missing_height_not_filled_with_fake_values(self):
        for key in ["vertical_datum", "terrain_model", "road_width_m", "turn_radius_m", "measured_clearance_m", "public_parking_confirmation"]:
            self.assertIsNone(self.survey[key], key)
        self.assertFalse(self.survey["continuous_streetview_coverage"])
        self.assertEqual(len(self.survey["visual_observations_from_previous_dossier"]), 6)
        self.assertTrue(self.route["rights"].startswith("© OpenStreetMap"))
        self.assertEqual(self.route["provenance"]["input_blob_sha"], self.survey["osm_source_blob_sha"])


if __name__ == "__main__":
    unittest.main()
