import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from coffa.road_shoulders import ramp_height, EdgeIndex, terrain_height


class ShoulderTest(unittest.TestCase):
    def test_ramp_meets_both_surfaces_and_has_zero_end_blend_slope(self):
        d = np.array([0, .0001, 2.5, 4.9999, 5])
        h = ramp_height(d, 1., 0., 5.)
        self.assertEqual(h[0], 1)
        self.assertAlmostEqual(h[-1], 0)
        self.assertLess(abs(h[1]-h[0])/.0001, .0001)
        self.assertLess(abs(h[-1]-h[-2])/.0001, .0001)
        self.assertTrue(np.all(np.diff(h) <= 0))

    def test_existing_high_ground_is_never_cut_by_shoulder(self):
        d = np.linspace(0, 5, 30)
        h = ramp_height(d, 1., np.sin(d)+.5, 5)
        self.assertTrue(np.all(h >= np.sin(d)+.5-1e-12))

    def test_boundary_height_uses_3d_edge_interpolation(self):
        index = EdgeIndex([[[0, 1, 0], [10, 3, 0]]])
        distance, height = index.sample([5, 15], [2, 0])
        np.testing.assert_allclose(distance, [2, 5])
        np.testing.assert_allclose(height, [2, 3])

    def test_ground_matches_engine_triangle_not_nearest_cell(self):
        heights = np.zeros((65, 65))
        heights[0, 1] = 2
        heights[1, 0] = 4
        heights[1, 1] = 10
        chunks = {(0, 0):{'heights_m':heights.ravel().tolist()}}
        np.testing.assert_allclose(terrain_height(chunks, [.5, 1.5], [.5, 1.5]), [1.5, 6.5])
        self.assertTrue(np.isnan(terrain_height(chunks, [200], [200])[0]))


if __name__ == '__main__':
    unittest.main()
