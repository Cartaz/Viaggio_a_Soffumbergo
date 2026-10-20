"""Grid interpolation tests; measured values only come from actual FVG downloads."""
import io
import unittest
from tools.profile_dtm_route import parse_asc, sample_bilinear


class DtmSamplingTests(unittest.TestCase):
    def test_center_and_bilinear_with_north_up(self):
        sample = b"""ncols 3
nrows 3
xllcorner 100
yllcorner 200
cellsize 10
nodata_value -9999
10 20 30
40 50 60
70 80 90
"""
        g = parse_asc(io.BytesIO(sample))
        # First ASCII row corresponds to northmost raster row.
        self.assertAlmostEqual(sample_bilinear(g, 105, 225), 10)
        self.assertAlmostEqual(sample_bilinear(g, 110, 220), 30)
        self.assertAlmostEqual(sample_bilinear(g, 115, 215), 50)
        self.assertIsNone(sample_bilinear(g, 99, 220))
        self.assertIsNone(sample_bilinear(g, 135, 220))

    def test_nodata_corners_do_not_interpolate(self):
        sample = b"""ncols 2
nrows 2
xllcorner 0
yllcorner 0
cellsize 10
nodata_value -9999
1 2
3 -9999
"""
        g = parse_asc(io.BytesIO(sample))
        self.assertIsNone(sample_bilinear(g, 10, 10))

    def test_invalid_grid_rejected(self):
        g = b"""ncols 2
nrows 2
xllcorner 0
yllcorner 0
cellsize 10
nodata_value -9999
1 2
3
"""
        with self.assertRaises(ValueError):
            parse_asc(io.BytesIO(g))
        with self.assertRaises(ValueError):
            parse_asc(io.BytesIO(g.replace(b"3\n", b"3 nan\n")))


if __name__ == "__main__":
    unittest.main()
