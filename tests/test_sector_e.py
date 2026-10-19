"""Check sector E anchor provenance without claiming complete road mapping."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_sector_e import build


class SectorEAnchorsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "docs/CIRCUITO_SOPRALLUOGO.md").read_text(encoding="utf-8")
        cls.expected = build(cls.source)
        cls.data = json.loads((ROOT / "data/geography/sector_e_anchors.geojson").read_text(encoding="utf-8"))

    def test_matches_source(self):
        self.assertEqual(self.data, self.expected)

    def test_points_accurate_and_ordered(self):
        pts = self.data["features"]
        self.assertEqual([p["id"] for p in pts], ["CIR-12", "CIR-13", "CIR-14"])
        self.assertEqual([p["properties"]["route_step"] for p in pts], [16, 17, 18])
        self.assertEqual([p["geometry"]["coordinates"] for p in pts],
                         [[13.379205, 46.1580732], [13.3623302, 46.1676159],
                          [13.3596292, 46.1659437]])
        self.assertTrue(all(p["geometry"]["type"] == "Point" for p in pts))
        self.assertEqual([p["properties"]["imagery_date"] for p in pts],
                         ["2023-05", "2024-08", "2024-08"])

    def test_rejects_unobserved_claims(self):
        self.assertFalse(self.data["road_geometry_available"])
        self.assertFalse(self.data["continuous_survey_completed"])
        self.assertFalse(self.data["terrain_elevation_available"])

    def test_missing_duplicate_rows_fail(self):
        with self.assertRaises(ValueError):
            build(self.source.replace("[CIR-12]", "[CIR-XX]"))
        row = next(line for line in self.source.splitlines() if line.startswith("| [CIR-13]"))
        with self.assertRaises(ValueError):
            build(self.source + "\n" + row + "\n")


if __name__ == "__main__":
    unittest.main()
