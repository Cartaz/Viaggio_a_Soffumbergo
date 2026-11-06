"""Synthetic CPU tests; no Unreal assets or source geometry are modified."""
import sys
from pathlib import Path
import unittest

import numpy as np
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))
from audit_swept_building_clearance import (
    build_swept_envelopes, candidate_intersections, projected_chassis
)


class SweepTests(unittest.TestCase):
    def setUp(self):
        self.q = np.array([[1, 0, 0, 0], [1, 0, 0, 0]], dtype=float)
        self.times = np.array([0., .05])

    def evaluate(self, positions, buildings, **kwargs):
        shape, pad, valid, *_ = build_swept_envelopes(
            np.asarray(positions, float), self.q, self.times, **kwargs
        )
        pairs, area = candidate_intersections(
            shape, pad, valid, np.asarray(buildings, dtype=object)
        )
        return pairs, area, valid

    def test_between_samples(self):
        positions = [[0, 0, 0], [4, 0, 0]]
        building = shapely.box(1.95, -.1, 2.05, .1)
        samples = projected_chassis(np.asarray(positions, float), self.q)
        self.assertFalse(any(shapely.intersects(p, building) for p in samples))
        pairs, areas, valid = self.evaluate(positions, [building], max_step_m=5.)
        self.assertTrue(valid[0])
        self.assertEqual(pairs.shape, (2, 1))
        self.assertGreater(areas[0], 0)

    def test_no_false_positive(self):
        pairs, areas, valid = self.evaluate(
            [[0, 0, 0], [.2, 0, 0]], [shapely.box(30, 30, 31, 31)]
        )
        self.assertTrue(valid[0])
        self.assertEqual(pairs.shape, (2, 0))
        self.assertEqual(len(areas), 0)

    def test_large_gap_skipped(self):
        self.times[1] = 2.
        pairs, _, valid = self.evaluate(
            [[0, 0, 0], [4, 0, 0]], [shapely.box(1.95, -.1, 2.05, .1)],
            max_step_m=5.
        )
        self.assertFalse(valid[0])
        self.assertEqual(pairs.shape, (2, 0))

    def test_rotation_sagitta_and_quaternion_sign(self):
        angle = np.pi/2
        self.q[1] = [np.cos(angle/2), 0, 0, np.sin(angle/2)]
        p = np.zeros((2, 3))
        sweeps, pad, valid, *_ = build_swept_envelopes(
            p, self.q, self.times, max_turn_deg=100
        )
        self.assertGreater(pad[0], .5)
        pairs, area = candidate_intersections(
            sweeps, pad, valid, np.asarray([shapely.box(-.2, 2.0, .2, 2.15)])
        )
        self.assertEqual(pairs.shape[1], 1)
        self.assertGreater(area[0], 0)
        self.q[1] *= -1
        _, pad2, valid2, *_ = build_swept_envelopes(
            p, self.q, self.times, max_turn_deg=100
        )
        self.assertEqual(bool(valid[0]), bool(valid2[0]))
        self.assertAlmostEqual(float(pad[0]), float(pad2[0]))

    def test_bad_quaternion_and_time_rejected(self):
        self.q[1] = [2, 0, 0, 0]
        with self.assertRaises(ValueError):
            build_swept_envelopes(np.zeros((2, 3)), self.q, self.times)
        self.q[1] = [1, 0, 0, 0]
        self.times[1] = 0
        with self.assertRaises(ValueError):
            build_swept_envelopes(np.zeros((2, 3)), self.q, self.times)


if __name__ == "__main__":
    unittest.main()
