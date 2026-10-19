"""Integrity of F-sector documentary anchors; does not validate a drivable road."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "geography"


class SectorFTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.instructions = json.loads((DATA / "settore_f_passaggi.json").read_text(encoding="utf-8"))
        cls.geo = json.loads((DATA / "settore_f_ancore.geojson").read_text(encoding="utf-8"))

    def test_complete_original_instruction_order(self):
        self.assertEqual(self.instructions["sector"], "F")
        self.assertEqual([s["passaggio"] for s in self.instructions["passaggi"]], list(range(19, 25)))
        distances = [s["distanza_app_m"] for s in self.instructions["passaggi"] if s["distanza_app_m"] is not None]
        self.assertEqual(distances, [13, 350, 650, 850, 9])
        self.assertEqual(sum(distances), self.instructions["distance_app_rounded_sum_m"])

    def test_anchors_are_only_two_dimensional_points(self):
        self.assertFalse(self.instructions["geometric_road_axis_available"])
        self.assertFalse(self.instructions["continuous_imagery_survey"])
        self.assertEqual(self.geo["type"], "FeatureCollection")
        features = self.geo["features"]
        self.assertEqual([f["id"] for f in features], self.instructions["anchor_ids"])
        self.assertEqual(len(features), 5)
        for f in features:
            self.assertEqual(f["geometry"]["type"], "Point")
            lon, lat = f["geometry"]["coordinates"]
            self.assertTrue(13.34 < lon < 13.37)
            self.assertTrue(46.15 < lat < 46.17)
            self.assertEqual(f["properties"]["horizontal_datum"], "WGS84")
            self.assertEqual(f["properties"]["elevation_status"], "unknown")
            self.assertTrue(f["properties"]["source_url"].startswith("https://"))
        self.assertEqual(sum(f["properties"]["source_kind"] == "previously_observed_panorama" for f in features), 3)
        self.assertEqual(sum(f["properties"]["source_kind"] == "maps_stop_marker" for f in features), 2)

    def test_source_and_limitations_not_omitted(self):
        self.assertTrue(self.instructions["reference_maps_url"].startswith("https://www.google.com/maps/dir/"))
        self.assertGreaterEqual(len(self.instructions["unverified"]), 5)
        self.assertFalse(self.instructions["tornanti_censiti"])


if __name__ == "__main__":
    unittest.main()
