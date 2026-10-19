"""Guardrails for the documented Sector A survey: observations are not a route."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "geography"


def _load(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


class SectorASurveyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.survey = _load("sector_a_survey.json")
        cls.observations = _load("sector_a_observations.geojson")

    def test_exact_source_maneuver_sequence(self):
        steps = self.survey["maneuvers"]
        self.assertEqual([x["step"] for x in steps], list(range(1, 7)))
        self.assertEqual([x["id"] for x in steps], [
            "A-01", "A-02", "A-03", "A-04", "A-05", "A-06"
        ])
        self.assertEqual([x["distance_m_app_rounded"] for x in steps],
                         [9, 44, 3400, 78, 78, 400])

    def test_rounded_length_not_a_survey(self):
        steps = self.survey["maneuvers"]
        cumulative = 0
        for entry in steps:
            cumulative += entry["distance_m_app_rounded"]
            self.assertEqual(entry["approx_cumulative_m_from_app_rounded"], cumulative)
        self.assertEqual(cumulative, 4009)
        self.assertEqual(self.survey["distance_sum_m_app_rounded"], cumulative)
        self.assertIsNone(self.survey["route_polyline"])

    def test_geojson_points_not_fake_road_or_altitudes(self):
        features = self.observations["features"]
        self.assertEqual(self.observations["type"], "FeatureCollection")
        self.assertEqual(len(features), 6)
        self.assertEqual({x["id"] for x in features},
                         {"A-START", "CIR-02", "CIR-03", "CIR-04", "CIR-05", "CIR-06"})
        for feat in features:
            self.assertEqual(feat["geometry"]["type"], "Point")
            lon, lat = feat["geometry"]["coordinates"]
            self.assertTrue(13.34 < lon < 13.38)
            self.assertTrue(46.12 < lat < 46.16)
            self.assertEqual(feat["properties"]["coordinate_quality"],
                             "routing_or_panorama_position_only_not_survey_control")
            self.assertTrue(feat["properties"]["source_url"].startswith("https://"))

    def test_all_streetview_anchors_linked(self):
        features = self.observations["features"]
        samples = [x for x in features if x["id"].startswith("CIR-")]
        self.assertEqual(len(samples), 5)
        for feat in samples:
            self.assertEqual(feat["properties"]["status"], "sampled_panorama")
            self.assertIn("pano=", feat["properties"]["source_url"])
            self.assertTrue(feat["properties"]["imagery_date"])

    def test_gaps_and_handoff_explicit(self):
        self.assertEqual(len(self.survey["gaps"]), 4)
        self.assertEqual([g["id"] for g in self.survey["gaps"]],
                         ["A-GAP-01", "A-GAP-02", "A-GAP-03", "A-GAP-04"])
        handoff = self.survey["handoff_to_sector_b"]
        self.assertEqual(handoff["boundary_panorama_id"], "CIR-06")
        self.assertEqual(handoff["next_instruction_step"], 7)
        self.assertTrue(handoff["next_step_not_part_of_sector_a"])
        self.assertIsNone(self.survey["terrain_model"])
        self.assertIsNone(self.survey["road_width_m"])


if __name__ == "__main__":
    unittest.main()
