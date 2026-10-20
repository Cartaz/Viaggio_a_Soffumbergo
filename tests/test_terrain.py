"""Analytical regressions: cell centres, missing data, orientation and seam geometry."""
import math
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from coffa.terrain import sample_grid, grid_triangles, clip_segment, lod_grid_error
from import_valle_lidar05 import read_grids


class TerrainTests(unittest.TestCase):
    def test_cell_centres_no_half_cell_shift(self):
        grid = [[10, 20, 30], [30, 40, 50], [50, 60, 70]]
        self.assertEqual(sample_grid(grid, 100.25, 199.75, 100, 200), 10)
        self.assertEqual(sample_grid(grid, 100.5, 199.5, 100, 200), 25)
        self.assertEqual(sample_grid(grid, 101.25, 198.75, 100, 200), 70)

    def test_no_extrapolation_or_nodata_filling(self):
        for grid, east in [([[1, 2], [3, 4]], -.1),
                            ([[1, -9999], [3, 4]], .25),
                            ([[1, math.nan], [3, 4]], .25)]:
            with self.assertRaises(ValueError):
                sample_grid(grid, east, .75, 0, 1)

    def test_planar_lods_exact_and_relief_error_measured(self):
        heights = [2*c+3*r for r in range(9) for c in range(9)]
        self.assertEqual(lod_grid_error(heights, 9, 4), 0)
        heights[4*9+3] += 12
        self.assertEqual(lod_grid_error(heights, 9, 4), 12)

    def test_clockwise_godot_front_and_complete_grid(self):
        faces = list(grid_triangles(3))
        self.assertEqual(len(faces), 8)
        for face in faces:
            points = [(i % 3, i // 3) for i in face]
            a, b, c = points
            # Positive x/z area => mathematical cross -Y => Godot CW front +Y.
            self.assertGreater((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]), 0)

    def test_clipping_retains_intersections_no_gap_bridges(self):
        self.assertEqual(clip_segment([-2, 1], [4, 1], [0, 0, 2, 2]), ([0., 1.], [2., 1.]))
        self.assertIsNone(clip_segment([-2, -1], [4, -1], [0, 0, 2, 2]))
        self.assertIsNone(clip_segment([-2, 0], [-1, 3], [0, 0, 2, 2]))

    def test_unrecognized_archive_rejected_before_decompression(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'untrusted.zip'
            path.write_bytes(b'not the verified original')
            with self.assertRaisesRegex(ValueError, 'checksum changed'):
                read_grids(path)


if __name__ == '__main__':
    unittest.main()
