"""Data-only tests: Sector C partial survey is explicitly not a completed road."""
import json
import math
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def distance(a,b):
    r=6371008.8
    la,lb=math.radians(a[1]),math.radians(b[1])
    dlat=lb-la
    dlon=math.radians(b[0]-a[0])
    x=math.sin(dlat/2)**2+math.cos(la)*math.cos(lb)*math.sin(dlon/2)**2
    return 2*r*math.asin(min(1,math.sqrt(x)))

class SectorCDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a=json.loads((ROOT/"data/geography/osm_survey.geojson").read_text())
        cls.source=next(f for f in a["features"] if f.get("id")=="way/547054266")
        cls.output=json.loads((ROOT/"data/geography/sector_c_partial.geojson").read_text())

    def test_only_one_real_segment_and_unchanged_vertices(self):
        ways=[f for f in self.output["features"] if f["geometry"]["type"]=="LineString"]
        self.assertEqual(len(ways),1)
        self.assertEqual(ways[0]["geometry"]["coordinates"],self.source["geometry"]["coordinates"])
        self.assertEqual(len(ways[0]["geometry"]["coordinates"]),97)

    def test_length_and_missing_coverage(self):
        points=self.source["geometry"]["coordinates"]
        measured=sum(distance(a,b) for a,b in zip(points,points[1:]))
        self.assertAlmostEqual(measured,self.output["properties"]["osm_length_m"],delta=0.02)
        self.assertTrue(1730<measured<1750)
        self.assertIn("PARTIAL",self.output["properties"]["coverage"])
        self.assertIn("NO elevations",self.output["coordinate_reference"])

    def test_observations_and_unverified_curves(self):
        fs=self.output["features"]
        anchors=[f for f in fs if f["properties"]["kind"]=="panorama_reference"]
        curves=[f for f in fs if f["properties"]["kind"]=="unverified_curve_candidate"]
        self.assertEqual({f["id"] for f in anchors},{"CIR-08","CIR-09","CIR-11"})
        self.assertEqual([f["properties"]["original_step"] for f in anchors],[9,10,11])
        self.assertEqual({f["id"] for f in curves},{"C-MAP-01","C-MAP-02"})
        for c in curves:
            self.assertTrue(c["properties"]["not_confirmed_hairpin"])
            self.assertIn(c["geometry"]["coordinates"],self.source["geometry"]["coordinates"])
        self.assertTrue(all(f["geometry"]["type"]=="Point" for f in anchors+curves))

if __name__=="__main__":
    unittest.main()
