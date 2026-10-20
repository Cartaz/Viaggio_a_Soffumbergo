"""Audit a real source-derived DTM snapshot without claiming road elevations."""
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from tools.plot_dtm_profile import render

ROOT = Path(__file__).resolve().parents[1]


class RealDtmSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads((ROOT / "data/geography/circuito_dtm10_terrain_profile_20261020.json").read_text(encoding="utf-8"))

    def test_real_source_metadata_and_all_point_coverage(self):
        p = self.profile
        self.assertEqual(p["source_archive_sha256"],
                         "5e98b18802da5e49ed8fb05f0e114fdc29612907164f934238514b3f9c87d39b")
        self.assertEqual(p["vertical_datum"], "UNKNOWN_NOT_VERIFIED")
        self.assertEqual(p["sampled_surface"], "BARE_EARTH_DTM_NOT_ASPHALT")
        self.assertFalse(p["godot_ready"])
        self.assertFalse(p["road_slope_verified"])
        self.assertTrue(p["all_samples_present"])
        self.assertEqual([s["sector"] for s in p["sectors"]], list("ABCVDEF"))
        self.assertEqual(sum(s["sample_count"] for s in p["sectors"]), 2394)
        self.assertEqual(sum(s["valid_count"] for s in p["sectors"]), 2394)
        self.assertAlmostEqual(p["total_length_projected_m"], 18884.861, places=2)

    def test_svg_is_reproducible_and_well_formed(self):
        original = (ROOT / "reports/terrain_10m_profile.svg").read_text(encoding="utf-8")
        self.assertEqual(render(self.profile), original)
        ET.fromstring(original)


if __name__ == "__main__":
    unittest.main()
