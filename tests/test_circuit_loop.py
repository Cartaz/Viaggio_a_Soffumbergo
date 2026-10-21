import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from coffa.loop_route import build, stationing, cut


class LoopTest(unittest.TestCase):
    # A closed circuit with one spur, and 40 m available before its junction.
    points = [[0, 0, 0], [40, 4, 0], [40, 6, -20], [40, 4, 0],
              [80, 8, 0], [80, 0, 80], [0, 0, 80], [0, 0, 0]]

    def test_spur_preserved_and_extra_distance_accounted(self):
        result = build(self.points)
        self.assertEqual(len(result['maneuvers']), 1)
        self.assertEqual([leg['gear'] for leg in result['legs']], [1, -1, 1])
        self.assertAlmostEqual(result['reference_length_m'], result['source_length_m'] + 30)
        self.assertEqual(result['legs'][0]['points_m'][-1], self.points[2])
        for first, second in zip(result['legs'], result['legs'][1:]):
            np.testing.assert_array_equal(first['points_m'][-1], second['points_m'][0])
        self.assertEqual(result['legs'][-1]['points_m'][-1], self.points[0])

    def test_reverse_reuses_original_3d_surface(self):
        reverse = build(self.points)['legs'][1]['points_m']
        np.testing.assert_array_equal(reverse[0], self.points[2])
        np.testing.assert_array_equal(reverse[1], self.points[1])
        np.testing.assert_allclose(reverse[-1], [25, 2.5, 0])

    def test_fixture_contains_same_reverse_and_outgoing_branch(self):
        result = build(self.points)
        fixture = result['maneuver_cases'][0]['legs']
        np.testing.assert_array_equal(fixture[1]['points_m'], result['legs'][1]['points_m'])
        self.assertIn(self.points[1], fixture[2]['points_m'])
        self.assertIn(self.points[4], fixture[2]['points_m'])

    def test_unclosed_insufficient_buffer_and_invalid_buffer_rejected(self):
        for points, buffer in [(self.points[:-1], 15), (self.points, 30),
                               (self.points, float('nan'))]:
            with self.assertRaises(ValueError):
                build(points, buffer)
        with self.assertRaises(ValueError):
            build([[0, 0, 0], [10, 0, 0], [10, 0, -10], [10, 0, 0],
                   [30, 0, 0], [30, 0, 30], [0, 0, 0]])

    def test_cut_preserves_heights_and_original_interior(self):
        p = np.array([[0, 0, 0], [10, 10, 0], [20, 15, 0]], dtype=float)
        np.testing.assert_allclose(cut(p, stationing(p), 5, 15),
                                   [[5, 5, 0], [10, 10, 0], [15, 12.5, 0]])


if __name__ == '__main__':
    unittest.main()
