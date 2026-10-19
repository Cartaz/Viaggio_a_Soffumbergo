"""Sector E: test map topology, provenance, and explicit absence of elevation."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_sector_e import WAYS, build, distance_2d


class SectorESurveyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.osm = json.loads((ROOT / "data/geography/osm_survey.geojson").read_text(encoding="utf-8"))
        cls.provenance = json.loads((ROOT / "data/geography/provenance.json").read_text(encoding="utf-8"))

    def test_cached_output_is_reproducible(self):
        expected = build(self.osm, self.provenance)
        actual = json.loads((ROOT / "data/geography/sector_e_planimetry.geojson").read_text(encoding="utf-8"))
        self.assertEqual(expected, actual)

    def test_known_chain_and_2d_geometry(self):
        result = build(self.osm, self.provenance)["features"][0]
        p = result["properties"]
        coords = result["geometry"]["coordinates"]
        self.assertEqual([x["osm_way_id"] for x in p["osm_way_ranges"]], list(WAYS))
        self.assertEqual(len(coords), 114)
        self.assertEqual(coords[0], [13.3933717, 46.1569967])
        self.assertEqual(coords[-1], [13.388935, 46.1463267])
        self.assertAlmostEqual(p["length_planimetric_m"], 1993.5, delta=0.2)
        self.assertTrue(all(len(c) == 2 for c in coords))
        self.assertEqual(p["elevation_status"], "unknown")
        self.assertEqual(p["vertical_datum"], "not_available")
        self.assertNotEqual(p["status"], "survey_complete")

    def test_severed_chain_fails_closed(self):
        bad = copy.deepcopy(self.osm)
        f = next(f for f in bad["features"] if f.get("properties", {}).get("osm_id") == WAYS[-1])
        # Last original coordinate is first when reversed, and must match the upstream way.
        f["geometry"]["coordinates"][-1][0] += 0.01
        with self.assertRaises(ValueError):
            build(bad, self.provenance)

    def test_excludes_nonmotorized_path(self):
        self.assertNotIn(159514556, WAYS)
        nonmotor = next(f for f in self.osm["features"]
                        if f.get("properties", {}).get("osm_id") == 159514556)
        self.assertEqual(nonmotor["properties"].get("motor_vehicle"), "no")

    def test_distance_never_treats_degrees_as_metres(self):
        self.assertGreater(distance_2d([13.393, 46.157], [13.394, 46.157]), 70)


if __name__ == "__main__":
    unittest.main()
