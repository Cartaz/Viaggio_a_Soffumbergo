"""Synthetic archive/DTM tests for selective Eagle route LiDAR acquisition."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from extract_eagle_route_surfaces import (
    expected_basename,matching_members,extract_verified
)


def raster_file():
    return (
        "ncols 3\nnrows 3\nxllcenter 372000\nyllcenter 5110000\n"
        "cellsize 0.5\nNODATA_value -9999\n"
        "100 101 102\n103 104 105\n106 107 108\n"
    ).encode("ascii")


class RouteAcquisitionTests(unittest.TestCase):
    def test_expected_product_names_are_explicit(self):
        self.assertEqual(expected_basename("06701307","DSM_FIRST"),"Ell_DSMfirst_06701307.asc")
        self.assertEqual(expected_basename("06701307","DBM"),"Ell_DBM_06701307.asc")
        for tile in ("../../12345678","06701307.zip","BAD","123"):
            with self.assertRaises(ValueError):
                expected_basename(tile,"DTM")

    def test_reject_missing_surface_product(self):
        with tempfile.TemporaryDirectory() as temp:
            zip_path=Path(temp)/"mock.zip"
            with zipfile.ZipFile(zip_path,"w") as z:
                z.writestr("Ell_DTM_06701307.asc",raster_file())
                z.writestr("Ell_DBM_06701307.asc",raster_file())
            with zipfile.ZipFile(zip_path,"r") as z:
                with self.assertRaisesRegex(ValueError,"Missing product"):
                    matching_members(z,["06701307"])

    def test_extract_all_roles_without_replacing_source_dtm(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            original=root/"dtm"
            original.mkdir()
            tile="06701307"
            dtm=original/expected_basename(tile,"DTM")
            dtm.write_bytes(raster_file())
            archive=root/"test.zip"
            with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
                for role in ("DTM","DBM","DSM_FIRST","DSM_LAST"):
                    z.writestr(expected_basename(tile,role),raster_file())
            output=root/"out"
            result=extract_verified(archive,original,output)
            self.assertEqual(result["status"],"complete")
            self.assertEqual(result["route_tile_count"],1)
            self.assertEqual(len(result["tiles"][tile]["products"]),3)
            self.assertTrue((output/"manifest.json").exists())
            self.assertEqual(dtm.read_bytes(),raster_file())
            self.assertFalse((output/expected_basename(tile,"DTM")).exists())
            self.assertFalse((root/"out.partial").exists())

    def test_dtm_mismatch_rejected_with_partial_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            original=root/"dtm"
            original.mkdir()
            tile="06701307"
            (original/expected_basename(tile,"DTM")).write_bytes(raster_file())
            archive=root/"test.zip"
            with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z:
                for role in ("DTM","DBM","DSM_FIRST","DSM_LAST"):
                    payload=raster_file().replace(b"100 101 102",b"110 101 102") if role=="DTM" else raster_file()
                    z.writestr(expected_basename(tile,role),payload)
            with self.assertRaisesRegex(ValueError,"does NOT match"):
                extract_verified(archive,original,root/"out")
            self.assertFalse((root/"out").exists())
            self.assertTrue((root/"out.partial").exists())


if __name__=="__main__":
    unittest.main()
