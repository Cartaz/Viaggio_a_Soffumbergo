"""Synthetic raster fixtures; does not claim FVG tiles have been downloaded."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.register_dtm import inspect_ascii_grid, register


HEADER = """ncols 3
nrows 2
xllcorner 400000
yllcorner 5100000
cellsize 1
NODATA_value -9999
"""


class DtmTests(unittest.TestCase):
    def test_grid_coverage_cells_and_inventory_idempotence(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            tile = folder / "test.asc"
            tile.write_text(HEADER + "3 6 -9999\n1 -2 0\n", encoding="utf-8")
            stats = inspect_ascii_grid(tile)
            self.assertEqual(stats["bounds_native_xy"], [400000, 5100000, 400003, 5100002])
            self.assertEqual((stats["valid_cells"], stats["nodata_cells"]), (5, 1))
            self.assertEqual((stats["grid_elevation_min"], stats["grid_elevation_max"]), (-2, 6))
            catalog = folder / "inventory.json"
            params = (tile, "https://irdat.regione.fvg.it/dataset/11826", "EPSG:7792",
                      "orthometric", "unverified", catalog, "example")
            item = register(*params)
            self.assertFalse(item["vertical_metadata_verified"])
            self.assertTrue(item["grid_not_road_surface"])
            register(*params)
            self.assertEqual(len(json.loads(catalog.read_text())["tiles"]), 1)
            tile.write_text(HEADER + "3 6 -9999\n1 -3 0\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Tile ID conflict"):
                register(*params)
            self.assertEqual(len(json.loads(catalog.read_text())["tiles"]), 1)

    def test_center_coordinates(self):
        with tempfile.TemporaryDirectory() as root:
            tile = Path(root) / "center.asc"
            tile.write_text("""NCOLS 2
NROWS 1
XLLCENTER 20
YLLCENTER 30
CELLSIZE 2
1 4
""", encoding="utf-8")
            self.assertEqual(inspect_ascii_grid(tile)["bounds_native_xy"], [19, 29, 23, 31])

    def test_corrupt_missing_extra_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            tile = Path(root) / "bad.asc"
            for bad in ["1 2\n", "1 2 3\n", "1 2 3\n4 5 6\n7 8 9\n",
                        "1 2 3\n4 nan 6\n", "-9999 -9999 -9999\n-9999 -9999 -9999\n"]:
                tile.write_text(HEADER + bad, encoding="utf-8")
                with self.assertRaises(ValueError, msg=repr(bad)):
                    inspect_ascii_grid(tile)
            tile.write_text(HEADER + "1 2 3\n4 5 6\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "HTTPS"):
                register(tile, "http://example.com", "EPSG:7792", "unknown")
            with self.assertRaisesRegex(ValueError, "CRS"):
                register(tile, "https://example.com", "EPSG:4326", "unknown")


if __name__ == "__main__":
    unittest.main()
