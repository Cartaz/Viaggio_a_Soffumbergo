"""Synthetic tests for LiDAR route coverage and NoData handling."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_mont_joanes_height_sources import parse_ascii_header
from audit_eagle_route_coverage import map_points_to_tiles,nearest_validity,ROLES


class RouteSurfaceCoverageTests(unittest.TestCase):
    def test_tile_assignment_is_strict_to_source_pixel_centers(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"Ell_DTM_1.asc"
            path.write_text(
                "ncols 3\nnrows 3\nxllcenter 0\nyllcenter 0\n"
                "cellsize 0.5\nNODATA_value -9999\n"
                "1 2 3\n4 5 6\n7 8 9\n",encoding="ascii")
            tile=parse_ascii_header(path)
            x=np.asarray([0,0.5,1,2,-0.1])
            y=np.asarray([0,1,0.5,2,0.5])
            assigned, groups=map_points_to_tiles(x,y,[("A",tile)])
            self.assertEqual(assigned.tolist(),[0,0,0,-1,-1])
            self.assertEqual(groups["A"].tolist(),[0,1,2])

    def test_raster_nodata_is_not_accepted_as_valid(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/"Ell_DTM_1.asc"
            file.write_text(
                "ncols 3\nnrows 3\nxllcenter 0\nyllcenter 0\n"
                "cellsize 0.5\nNODATA_value -9999\n"
                "1 2 3\n4 5 6\n7 8 9\n",encoding="ascii")
            tile=parse_ascii_header(file)
            data=np.ones((3,3),dtype=np.float32)
            bad=data.copy()
            bad[0,0]=-9999.
            arrays={role:data.copy() for role in ROLES}
            arrays["DBM"]=bad
            flags=nearest_validity(tile,arrays,np.asarray([0.,1.]),np.asarray([1.,0.]))
            self.assertEqual(flags["DTM"].tolist(),[True,True])
            self.assertEqual(flags["DBM"].tolist(),[False,True])
            self.assertEqual(flags["DSM_FIRST"].tolist(),[True,True])


if __name__=="__main__":
    unittest.main()
