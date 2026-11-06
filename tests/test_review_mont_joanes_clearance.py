"""Synthetic source-review tests, no real GIS or Unreal project changes."""
import sys
from pathlib import Path
import unittest

import numpy as np
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from review_mont_joanes_clearance import (
    actual_asphalt_polygon, locate_geometry, render_plan, svg_path
)


class SourcePlanTests(unittest.TestCase):
    def test_asphalt_geometry_keeps_centimeter_units_and_clip(self):
        class Road:
            polygons = np.asarray([
                shapely.box(0, 0, 200, 100),
                shapely.box(500, 500, 600, 600)
            ], dtype=object)
            tree = shapely.STRtree(polygons)

        clip = shapely.box(.5, .2, 2.5, .8)
        actual = actual_asphalt_polygon(Road(), clip)
        self.assertAlmostEqual(actual.area, 1.5*.6, 8)
        self.assertEqual(shapely.distance(actual, shapely.Point(1, .5)), 0.0)
        self.assertTrue(actual_asphalt_polygon(Road(), shapely.box(20, 20, 21, 21)).is_empty)

    def test_polygon_holes_in_svg_paths(self):
        shape = shapely.Polygon(
            [(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)],
            holes=[[(1, 1), (2, 1), (2, 2), (1, 2), (1, 1)]]
        )
        drawing = svg_path(shape, 0, 0, 10, 120, 120)
        self.assertEqual(drawing.count(" Z"), 2)
        self.assertTrue(drawing.startswith("M"))

    def test_original_osm_ring_transform(self):
        class IdentityProjection:
            def transform(self, longitude, latitude):
                return longitude, latitude

        shape = {
            "geometry": {
                "type": "LineString",
                "coordinates": [[1, 2], [3, 2], [3, 4], [1, 4], [1, 2]]
            }
        }
        polygon = locate_geometry(shape, IdentityProjection(), np.array([0, 6, 0]))
        self.assertEqual(polygon.geom_type, "Polygon")
        self.assertAlmostEqual(float(polygon.area), 4.0, 7)
        self.assertAlmostEqual(float(polygon.centroid.y), 3.0, 7)

    def test_published_source_figures_are_well_formed(self):
        from xml.etree import ElementTree
        folder = Path(__file__).resolve().parents[1] / "docs/figure_mont_joanes"
        for way in ("36158227", "36158219"):
            path = folder / ("plan_" + way + ".svg")
            tree = ElementTree.parse(path)
            self.assertTrue(tree.getroot().tag.endswith("svg"))
            self.assertIn("OpenStreetMap", path.read_text(encoding="utf-8"))
        page = (folder / "review.html").read_text(encoding="utf-8")
        self.assertIn("Canal di Grivò", page)
        self.assertNotIn("<img ", page)

    def test_preview_marks_not_surveyed(self):
        poly = shapely.box(-1, -1, 1, 1)
        result = render_plan(
            {"source_id": "way/36158227", "center_UE_xy_m": [0, 0]},
            road=poly, route=shapely.LineString([(-2, 0), (2, 0)]),
            chassis=poly, swept=poly, buildings={"way/36158227": poly},
            panorama=[{
                "position_UE_xy_m": [3, 3],
                "headings_actually_seen": [281, 340]
            }]
        )
        self.assertIn("<svg", result)
        self.assertIn("north up", result)
        self.assertIn("fill-rule=\"evenodd\"", result)
        self.assertEqual(result.count('r="5.2"'), 1)


if __name__ == "__main__":
    unittest.main()
