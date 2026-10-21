import json
from pathlib import Path
import sys
import unittest
import numpy as np
import shapely
from shapely import box, Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from coffa.road_construction import (SegmentIndex, design_profile, road_footprint,
                                     triangulate_surface, validate_config)


class ConstructionTest(unittest.TestCase):
    def test_spatial_nearest_matches_exhaustive_and_has_bounded_radius(self):
        # Nearby branches at different heights must not be averaged.
        p = np.array([[0, 0, 0], [40, 4, 0], [40, 10, 6], [0, 10, 6]], dtype=float)
        idx = SegmentIndex(p)
        rng = np.random.default_rng(208)
        q = rng.uniform([-4, -5], [45, 11], size=(300, 2))
        distance, height, segment = idx.query(q[:, 0], q[:, 1], 20)
        a, d = p[:-1, [0, 2]], np.diff(p[:, [0, 2]], axis=0)
        t = np.clip(((q[:, None]-a)*d).sum(axis=2)/(d*d).sum(axis=1), 0, 1)
        dist = np.linalg.norm(q[:, None]-a-t[:, :, None]*d, axis=2)
        expected = dist.argmin(axis=1)
        np.testing.assert_array_equal(segment, expected)
        np.testing.assert_allclose(distance, dist[np.arange(len(q)), expected])
        np.testing.assert_allclose(height, p[expected, 1]+t[np.arange(len(q)), expected]*np.diff(p[:, 1])[expected])
        distance, height, segment = idx.query([10, 10, 1000], [1, 5, 1000], 4)
        np.testing.assert_allclose(height[:2], [1, 10])
        self.assertTrue(np.isinf(distance[2]) and np.isnan(height[2]) and segment[2] == -1)

    def test_exact_retrace_has_one_surface_without_shortcut(self):
        p = np.array([[0, 1, 0], [15, 1, 0], [15, 1, 8], [0, 1, 8], [15, 1, 8], [15, 1, 0], [0, 1, 0]])
        g = road_footprint(p, 4)
        once = road_footprint(p[:4], 4)
        self.assertAlmostEqual(g.area, once.area, places=8)
        self.assertFalse(g.covers(shapely.Point(5, 4)))  # preserve the hairpin's inner gap
        vertices, faces = triangulate_surface(g, SegmentIndex(p), 3, 2.01)
        v = np.asarray(vertices)
        area = 0
        for face in faces:
            f = v[face]
            self.assertLess(np.cross(f[1]-f[0], f[2]-f[0])[1], 0)
            triangle = Polygon(f[:, [0, 2]])
            self.assertLess(triangle.difference(g).area, 1e-5)
            area += triangle.area
        self.assertAlmostEqual(area, g.area, places=4)

    def test_mesh_preserves_hole_and_chunk_seam(self):
        p = np.array([[0, 0, 0], [16, 0, 0], [16, 0, 16], [0, 0, 16], [0, 0, 0]])
        idx = SegmentIndex(p)
        g = road_footprint(p, 4)
        self.assertEqual(len(g.interiors), 1)
        borders = []
        for bounds in [box(-4, -4, 8, 20), box(8, -4, 20, 20)]:
            part = g.intersection(bounds)
            vertices, faces = triangulate_surface(part, idx, 3, 2.01)
            v = np.asarray(vertices)
            borders.append(sorted(tuple(x) for x in v[np.abs(v[:, 0]-8) < 1e-6]))
            area = sum(Polygon(v[t][:, [0, 2]]).area for t in faces)
            self.assertAlmostEqual(area, part.area, places=4)
        self.assertEqual(borders[0], borders[1])

    def test_closed_profile_unifies_duplicate_positions_and_reports_reversal(self):
        points = [[0, 0, 0], [2, 0, 0], [4, 4, 0], [2, 0, 0], [0, 0, 0], [0, 0, 2], [0, 0, 0]]
        route = [{'points_m':points}]
        p, raw, station, angles, stats = design_profile(route, 3, .15)
        np.testing.assert_equal(p[0], p[-1])
        np.testing.assert_equal(p[1], p[3])
        self.assertEqual(stats['repeated_node_count'], 2)
        self.assertGreaterEqual(np.count_nonzero(angles > 179.99), 2)
        self.assertGreater(station[-1], 0)
        with self.assertRaisesRegex(ValueError, 'closed'):
            design_profile([{'points_m':points[:-1]}], 3, .15)

    def test_invalid_parameter_fails(self):
        path = Path(__file__).resolve().parents[1]/'data/config/circuit_construction.json'
        config = json.loads(path.read_text())
        validate_config(config)
        config['width_m'] = float('nan')
        with self.assertRaises(ValueError):
            validate_config(config)


if __name__ == '__main__':
    unittest.main()
