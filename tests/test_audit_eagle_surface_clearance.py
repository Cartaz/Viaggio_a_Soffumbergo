"""Offline tests for area-weighted DTM/DBM/DSM evidence at native vehicle contacts."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import shapely

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_eagle_surface_clearance import (
    weighted_surface_summary,to_native_utm,case_intervals
)
from audit_mont_joanes_height_sources import parse_ascii_header


def grid_file(path):
    path.write_text(
        "ncols 4\nnrows 3\nxllcenter 10\nyllcenter 20\ncellsize 0.5\nNODATA_value -9999\n"
        "100 100 100 100\n100 100 100 100\n100 100 100 100\n",encoding="ascii")
    return parse_ascii_header(path)


class VerticalConflictTests(unittest.TestCase):
    def test_area_weighted_contributions_on_two_cells(self):
        with tempfile.TemporaryDirectory() as folder:
            grid=grid_file(Path(folder)/"Ell_DTM_1.asc")
            dtm=np.full((3,4),100.,dtype=np.float32)
            dbm=dtm.copy()
            # Northernmost row, x=10.0 => 6m, x=10.5 => 0m.
            dbm[0,0]=106.
            arr={"DTM":dtm,"DBM":dbm,
                 "DSM_FIRST":dbm.copy(),"DSM_LAST":dtm.copy()}
            # Region covers 0.25 m² in first cell + 0.125 m² in second.
            region=shapely.box(9.75,20.75,10.5,21.25)
            summary=weighted_surface_summary(region,grid,arr)
            self.assertAlmostEqual(summary["intersected_map_area_m2"],.375)
            self.assertAlmostEqual(summary["DBM"]["area_m2"],.375)
            self.assertAlmostEqual(summary["DBM"]["mean_delta_m"],4.)
            self.assertAlmostEqual(summary["DBM"]["fraction_of_valid_area_above_1_5m"],2/3)
            self.assertAlmostEqual(summary["DSM_LAST"]["max_delta_m"],0.)
            self.assertFalse(summary["DBM"]["weighted_height_is_surveyed_wall"])

    def test_missing_raster_values_reported_not_zero_height(self):
        with tempfile.TemporaryDirectory() as folder:
            grid=grid_file(Path(folder)/"Ell_DTM_1.asc")
            dtm=np.full((3,4),100.,dtype=np.float32)
            dbm=dtm.copy()
            dbm[0,0]=np.nan
            arr={"DTM":dtm,"DBM":dbm,
                 "DSM_FIRST":dbm.copy(),"DSM_LAST":dtm.copy()}
            region=shapely.box(9.75,20.75,10.25,21.25)
            summary=weighted_surface_summary(region,grid,arr)
            self.assertEqual(summary["valid_cells"],1)
            self.assertIsNone(summary["DBM"])
            self.assertAlmostEqual(summary["DSM_LAST"]["area_m2"],.25)

    def test_native_coordinate_reflection(self):
        polygon=shapely.box(10,20,12,22)
        out=to_native_utm(polygon,np.array([373000,5114000,100]))
        self.assertEqual(out.bounds,(373010.,5113978.,373012.,5113980.))
        self.assertAlmostEqual(out.area,polygon.area)

    def test_rolling_intervals_are_exact_not_rounded(self):
        t=np.array([10.,10.05,10.10,10.15,10.20])
        case={"interval_sequences":[[10.,10.10],[10.15,10.20]]}
        self.assertEqual(case_intervals(case,t,is_fvg=True),[0,1,3])
        case={"first_time_s":10.05,"last_time_s":10.20}
        self.assertEqual(case_intervals(case,t,is_fvg=False),[1,2,3])
        case["last_time_s"]=10.22
        with self.assertRaises(ValueError):
            case_intervals(case,t,is_fvg=False)

    def test_disjoint_region_has_no_surface_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            grid=grid_file(Path(folder)/"Ell_DTM_1.asc")
            all_ones=np.ones((3,4),dtype=np.float32)
            arrays={role:all_ones for role in ("DTM","DBM","DSM_FIRST","DSM_LAST")}
            out=weighted_surface_summary(shapely.GeometryCollection(),grid,arrays)
            self.assertEqual(out["covered_raster_area_m2"],0.)
            self.assertIsNone(out["DBM"])


if __name__=="__main__":
    unittest.main()
