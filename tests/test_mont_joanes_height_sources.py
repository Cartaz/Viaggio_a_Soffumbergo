"""Offline verification of ESRI 0.5m ellipsoidal elevation import guards."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_mont_joanes_height_sources import (
    parse_ascii_header, sample_grid, inspect_optional_manifest,
    points_from_reports, file_hash, REGIONAL_SOURCE
)


def make_grid(path, *, corner=False, nodata=False):
    first = "xllcorner     9.75\nyllcorner     19.75\n" if corner else "xllcenter     10\nyllcenter     20\n"
    body = ("ncols         3\nnrows         3\n" + first
            + "cellsize      0.5\nNODATA_value -9999\n"
            + "10 20 30\n40 50 60\n70 80 " + ("-9999" if nodata else "90") + "\n")
    path.write_text(body, encoding="ascii")


class HeightSourceTests(unittest.TestCase):
    def test_row_direction_and_bilinear(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "Ell_DTM_1234.asc"
            make_grid(file)
            grid = parse_ascii_header(file)
            self.assertTrue(grid.covers(10.25, 20.25))
            self.assertAlmostEqual(sample_grid(grid, 10.25, 20.25), 60.)
            self.assertAlmostEqual(sample_grid(grid, 10, 21), 10.)
            self.assertAlmostEqual(sample_grid(grid, 11, 20), 90.)
            self.assertIsNone(sample_grid(grid, 100, 100))

    def test_corner_registration_equivalent_to_center(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "Ell_DTM_1234.asc"
            make_grid(file, corner=True)
            grid = parse_ascii_header(file)
            self.assertAlmostEqual(grid.x_center, 10.)
            self.assertAlmostEqual(grid.y_center, 20.)
            self.assertAlmostEqual(sample_grid(grid, 10.25, 20.25), 60.)

    def test_nodata_does_not_become_fake_height(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "Ell_DTM_1234.asc"
            make_grid(file, nodata=True)
            grid = parse_ascii_header(file)
            self.assertIsNone(sample_grid(grid, 10.75, 20.25))
            self.assertAlmostEqual(sample_grid(grid, 10, 21), 10.)

    def test_wrong_resolution_and_missing_header_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "Ell_DTM_1234.asc"
            make_grid(file)
            file.write_text(file.read_text().replace("0.5", "1.0"),encoding="ascii")
            with self.assertRaises(ValueError):
                parse_ascii_header(file)
            file.write_text("not a grid\n",encoding="ascii")
            with self.assertRaises((ValueError,StopIteration)):
                parse_ascii_header(file)

    def test_verified_surface_manifest_hash_and_datum(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            grid = directory / "Ell_DBM_1234.asc"
            manifest_file = directory / "source.json"
            make_grid(grid)
            source = {
                "horizontal_crs": "EPSG:6708",
                "vertical_datum": "ellipsoidal",
                "source_catalog_url": REGIONAL_SOURCE,
                "products": {
                    "DBM": {
                        "product": "DBM",
                        "path":str(grid),
                        "sha256":file_hash(grid),
                        "source_download_url":"https://eaglefvg.regione.fvg.it/eagle/main.aspx?configuration=guest",
                        "original_basename":grid.name
                    }
                }
            }
            manifest_file.write_text(json.dumps(source),encoding="utf-8")
            selected = inspect_optional_manifest(manifest_file)
            self.assertIn("DBM", selected)
            self.assertEqual(selected["DBM"][1], hashlib.sha256(grid.read_bytes()).hexdigest())
            source["vertical_datum"] = "orthometric"
            manifest_file.write_text(json.dumps(source),encoding="utf-8")
            with self.assertRaises(ValueError):
                inspect_optional_manifest(manifest_file)
            source["vertical_datum"] = "ellipsoidal"
            source["products"]["DBM"]["sha256"] = "0"*64
            manifest_file.write_text(json.dumps(source),encoding="utf-8")
            with self.assertRaises(ValueError):
                inspect_optional_manifest(manifest_file)

    def test_source_hotspots_are_distinct_and_build_locked(self):
        regional = {
            "complete":True,"native_build_id":"f4373a62b482",
            "regional_layers":{"DBS_EDIFICATO":{"cases":[{
                "regional_id":"DBS_EDIFICATO.569250",
                "approx_peak_wgs84_lat_lon":[46.1665,13.3603]
            }]}}
        }
        osm = {
            "build_id":"f4373a62b482","diagnostic_completed":True,
            "cases":[{"source_id":"way/36158227",
                      "peak_vehicle_center_wgs84":[46.1673,13.3607]},
                     {"source_id":"way/36162093",
                      "peak_vehicle_center_wgs84":[46.1234,13.35]}]
        }
        result = points_from_reports(regional,osm)
        self.assertEqual(len(result),2)
        self.assertEqual([r["source_id"] for r in result],
                         ["DBS_EDIFICATO.569250","way/36158227"])
        osm["build_id"]="wrong"
        with self.assertRaises(ValueError):
            points_from_reports(regional,osm)


if __name__ == "__main__":
    unittest.main()
