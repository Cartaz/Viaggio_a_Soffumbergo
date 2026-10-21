import copy
import json
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from build_parking_pilot import design


class ParkingDesignTests(unittest.TestCase):
    def setUp(self):
        self.road = {'points_m': [[0, s*.08, -s] for s in range(0, 605, 2)]}

    def test_original_input_preserved_and_approach_unchanged(self):
        before = copy.deepcopy(self.road)
        p, s, _, _, _ = design(self.road)
        self.assertEqual(self.road, before)
        np.testing.assert_allclose(p[s < 550], np.array(before['points_m'])[s < 550])

    def test_level_apron_and_declared_synthetic_dimensions(self):
        p, s, vertices, triangles, parking = design(self.road)
        np.testing.assert_allclose(p[s >= 582, 1], parking['level_m'])
        widths = np.linalg.norm(vertices[1::2]-vertices[::2], axis=1)
        self.assertAlmostEqual(widths[0], 4.5)
        self.assertAlmostEqual(widths[-1], 8)
        self.assertFalse(parking['surveyed_dimensions'])
        for face in vertices[triangles]:
            self.assertLess(np.cross(face[1]-face[0], face[2]-face[0])[1], 0)

    def test_short_input_rejected(self):
        with self.assertRaises(ValueError):
            design({'points_m': [[0, 0, 0], [0, 0, -100]]})
