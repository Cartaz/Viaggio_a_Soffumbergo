import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from coffa.geography import A, ecef, radius_horizontal, resample, road_strip, to_godot
from prepare_route import prepare
from fetch_geography import convert


class GeographyTests(unittest.TestCase):
    def test_ecef_analytic_equator(self):
        self.assertEqual(ecef([0, 0, 0]), (A, 0, 0))
        p = ecef([90, 0, 100])
        self.assertAlmostEqual(p[0], 0, places=6)
        self.assertEqual(p[1], A + 100)

    def test_local_axes_and_altitude(self):
        origin = [13.393, 46.157, 300]
        self.assertEqual(to_godot(origin, origin), [0, 0, 0])
        east = to_godot([13.394, 46.157, 300], origin)
        north = to_godot([13.393, 46.158, 300], origin)
        up = to_godot([13.393, 46.157, 310], origin)
        self.assertGreater(east[0], 70)
        self.assertLess(north[2], -100)
        self.assertAlmostEqual(up[1], 10, places=7)

    def test_no_height_no_route(self):
        with self.assertRaises(ValueError):
            to_godot([13, 46], [13, 46, 0])
        feature = {"type": "Feature", "properties": {},
                   "geometry": {"type": "LineString", "coordinates": [[13, 46], [14, 46]]}}
        with self.assertRaises(ValueError):
            prepare(feature, 5, 3)

    def test_densification_preserves_hairpin_vertices(self):
        points = [[0, 0, 0], [20, 1, 0], [20, 2, 2], [0, 3, 2]]
        dense = resample(points, 3)
        for p in points:
            self.assertIn(p, dense)
        self.assertTrue(all(math.dist(a, b) <= 3.000001 for a, b in zip(dense, dense[1:])))

    def test_static_radius_and_degenerate_input(self):
        self.assertAlmostEqual(radius_horizontal([20, 0, 0], [0, 0, 20], [-20, 0, 0]), 20)
        self.assertIsNone(radius_horizontal([0, 0, 0], [1, 0, 0], [2, 0, 0]))
        with self.assertRaises(ValueError):
            resample([[0, 0, 0], [0, 0, 0]])

    def test_strip_width_and_godot_winding(self):
        v, triangles = road_strip([[0, 0, 0], [0, 1, -10]], 5)
        self.assertAlmostEqual(math.dist(v[0], v[1]), 5)
        for t in triangles:
            a, b, c = [v[i] for i in t]
            # In Godot's clockwise convention geometric cross product points down.
            cross_y = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
            self.assertLess(cross_y, 0)

    def test_osm_incomplete_geometry_rejected(self):
        with self.assertRaises(ValueError):
            convert({"elements": [{"type": "way", "id": 1, "nodes": [1, 2], "tags": {"highway": "road"}}]})

    def test_osm_nodes_are_not_assumed_elevated(self):
        data = {"elements": [{"type": "node", "id": 1, "lon": 13, "lat": 46},
                             {"type": "node", "id": 2, "lon": 13.01, "lat": 46},
                             {"type": "way", "id": 4, "nodes": [1, 2], "tags": {"highway": "residential"}}]}
        result = convert(data)
        self.assertEqual(len(result["features"][0]["geometry"]["coordinates"][0]), 2)
        self.assertIn("no elevations", result["coordinate_reference"])


if __name__ == "__main__":
    unittest.main()
