"""Validate official 0.5 m tile footprints: metadata is not terrain elevation."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data/geography/lidar05_valle_tile_manifest_20261020.json"


class LidarHalfMeterTileManifestTests(unittest.TestCase):
    def test_exact_wfs_tiles_and_acquired_ellipsoidal_rasters(self):
        doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(doc["raster_downloads_completed"], 4)
        self.assertFalse(doc["vertical_metadata_verified_independently"])
        self.assertIn("ellipsoidal", doc["vertical_datum_operator_declared"])
        self.assertFalse(doc["direct_raster_url_known"])
        evidence = doc["user_archive_verification"]
        self.assertEqual(evidence["archive_sha256"],
                         "bd715cd7c9b3820646f93f9e918cab1159950f47c2df5fc39e0218fc564a6a14")
        self.assertEqual(evidence["valid_grid_cells"], 12096000)
        self.assertEqual(evidence["unique_mosaic_cells"], 11008000)
        self.assertEqual(evidence["overlap_max_height_delta_m"], 0)
        self.assertFalse(evidence["ready_as_drivable_surface"])
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
            self.assertEqual(tile["nodata_cells"], 0)
            self.assertEqual((tile["ncols"], tile["nrows"]), (1800,1680))
            self.assertEqual(len(tile["asc_sha256"]), 64)
            self.assertEqual(tile["asc_member"], "Ell_DTM_" + tile["code"] + ".asc")


if __name__ == "__main__":
    unittest.main()
