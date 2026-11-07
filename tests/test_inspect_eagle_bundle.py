"""Offline synthetic tests for post-download Eagle.fvg ZIP inventory."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))
from inspect_eagle_bundle import safe_name, classify_entry, inspect


def create_zip(path, entries):
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        for name,payload in entries:
            z.writestr(name,payload)


class EagleBundleTests(unittest.TestCase):
    def test_classify_dsm_dbm_dtm_and_lidar(self):
        self.assertEqual(classify_entry("Altitude/Ell_DSM_Primo_06701307.asc")["role_guess"],"DSM")
        self.assertEqual(classify_entry("Altitude/Ell_DBM_06701307.asc")["datum_guess"],"ellipsoidal")
        self.assertEqual(classify_entry("Altitude/Ort_DTM_06701307.asc")["datum_guess"],"orthometric")
        self.assertEqual(classify_entry("Laser/LAS Ellissoidico/D461...las")["role_guess"],"POINT_CLOUD")
        self.assertEqual(classify_entry("maps/FAEDIS.pdf")["role_guess"],"OTHER")

    def test_zip_path_traversal_forbidden(self):
        for name in ("../x.asc","/tmp/x.asc","C:/tmp/x.asc","folder\\bad.asc",
                     "sub//bad.asc","sub/./x.asc","a:ads.asc","folder/x.asc."):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    safe_name(name)
        self.assertEqual(safe_name("lidar/ell_DSM_06701307.asc"),"lidar/ell_DSM_06701307.asc")

    def test_inventory_and_selective_extraction(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            archive=root/"download-example.zip"
            create_zip(archive,[
                ("lidar/Ell_DBM_06701307.asc",b"grid data\n"),
                ("lidar/Ell_DSM_First_06701307.asc",b"DSM data\n"),
                ("lidar/Ell_DTM_06601223.asc",b"elsewhere\n"),
                ("map/shape.shp",b"shape")
            ])
            result=inspect(archive,root/"report",extract=True)
            self.assertEqual(result["member_count"],4)
            self.assertEqual(len(result["target_candidates"]),2)
            self.assertEqual(len(result["extracted"]),2)
            self.assertEqual((root/"report/target_tile/lidar/Ell_DBM_06701307.asc").read_bytes(),b"grid data\n")
            self.assertTrue((root/"report/inventory.json").exists())
            self.assertIsNone(result["archive_sha256"])
            self.assertTrue(result["sha256_pending_full_pass"])

    def test_reject_archive_in_progress(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); archive=root/"download-example.zip"
            create_zip(archive,[("lidar/Ell_DBM_06701307.asc",b"data")])
            (root/"download-example.random.zip.part").write_bytes(b"partial")
            with self.assertRaises(RuntimeError):
                inspect(archive,root/"blocked")
            self.assertFalse((root/"blocked").exists())

    def test_reject_duplicates_and_traversal_without_extract(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);archive=root/"bad.zip"
            create_zip(archive,[("../outside.txt",b"x")])
            with self.assertRaises(ValueError):
                inspect(archive,root/"report")
            self.assertFalse((root/"report").exists())
            create_zip(archive,[
                ("LIDAR/Ell_DBM_06701307.asc",b"x"),
                ("lidar/ell_dbm_06701307.asc",b"y")
            ])
            with self.assertRaises(ValueError):
                inspect(archive,root/"report")
            self.assertFalse((root/"report").exists())

    def test_never_overwrite_an_existing_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); archive=root/"download-example.zip"
            create_zip(archive,[("lidar/Ell_DBM_06701307.asc",b"data")])
            inspect(archive,root/"report")
            with self.assertRaises(FileExistsError):
                inspect(archive,root/"report")


if __name__=="__main__":
    unittest.main()
