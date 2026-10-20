"""Validate official 0.5 m tile footprints: metadata is not terrain elevation."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/geography/lidar05_valle_tile_manifest_20261020.json"


class LidarHalfMeterTileManifestTests(unittest.TestCase):
    def test_exact_official_wfs_tile_ids_and_declared_gaps(self):
        doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(doc["raster_downloads_completed"], 0)
        self.assertIsNone(doc["vertical_datum_requested"])
        self.assertFalse(doc["direct_raster_url_known"])
        self.assertEqual(doc["grid_resolution_m"], 0.5)
        self.assertEqual(doc["horizontal_crs_native"], "EPSG:6708")
        self.assertEqual(doc["wfs_bbox_requested_lonlat"], [13.39, 46.155, 13.395, 46.159])
        codes = {t["code"] for t in doc["tiles"]}
        self.assertEqual(codes, {"06701210", "06701211", "06701214", "06701215"})
        self.assertEqual(len(codes), len(doc["tiles"]))
        ids = {t["wfs_id"] for t in doc["tiles"]}
        self.assertEqual(len(ids), 4)
        for tile in doc["tiles"]:
            xmin, ymin, xmax, ymax = tile["bounds_native_xy"]
            self.assertLess(xmin, xmax)
            self.assertLess(ymin, ymax)
            self.assertEqual(xmax - xmin, 900)
            self.assertEqual(ymax - ymin, 840)
            self.assertEqual(tile["crtn"], "067012")


if __name__ == "__main__":
    unittest.main()
