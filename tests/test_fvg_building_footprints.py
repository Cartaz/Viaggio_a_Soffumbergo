"""Offline synthetic tests for FVG WFS source comparison and full-lap grouping."""
import json
from pathlib import Path
import sys
import unittest

import numpy as np
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from fetch_fvg_building_footprints import (
    query_parameters, validate_snapshot
)
from compare_fvg_building_footprints import (
    compare_layer, to_unreal_shapes, draw_overlay
)
from audit_fvg_full_lap_clearance import (
    segment_ranges, summarize_hits
)
from render_fvg_hotspot_overview import render_overview


def mock_fvg_features(*, count=1, crs="urn:ogc:def:crs:EPSG::6708",
                      geometry=None):
    base = geometry or {
        "type": "Polygon",
        "coordinates": [
            [[373400, 5113900, 0], [373405, 5113900, 0],
             [373405, 5113905, 0], [373400, 5113905, 0],
             [373400, 5113900, 0]]
        ]
    }
    return json.dumps({
        "type": "FeatureCollection",
        "totalFeatures": count,
        "crs": {"type": "name", "properties": {"name": crs}},
        "features": [
            {"type": "Feature", "id": "DBS_EDIFICATO." + str(i+1),
             "properties": {"CLASSE": "edificato"}, "geometry": base}
            for i in range(count)
        ]
    }).encode("utf-8")


class RegionalSourceTests(unittest.TestCase):
    def test_wfs_uses_native_projection(self):
        params = query_parameters(
            "DBS_EDIFICATO", (373300, 5113800, 373500, 5114000)
        )
        self.assertEqual(params["bbox"], "373300.000000,5113800.000000,373500.000000,5114000.000000")
        self.assertEqual(params["typeName"], "EDIFICI:DBS_EDIFICATO")
        self.assertEqual(params["maxFeatures"], "1000")
        with self.assertRaises(ValueError):
            query_parameters("untrusted_layer", (1, 2, 3, 4))

    def test_crs_fingerprints_duplicate_and_bbox_guard(self):
        bbox = (373390., 5113890., 373420., 5113920.)
        self.assertEqual(
            len(validate_snapshot(mock_fvg_features(), "DBS_EDIFICATO", bbox)["features"]),
            1
        )
        wrong_crs = mock_fvg_features(crs="EPSG:4326")
        outside_box = mock_fvg_features(geometry={
            "type": "Polygon", "coordinates": [
                [[100, 100], [110, 100], [110, 110], [100, 100]]
            ]
        })
        for blob in (wrong_crs, outside_box):
            with self.assertRaises(ValueError):
                validate_snapshot(blob, "DBS_EDIFICATO", bbox)
        example = json.loads(mock_fvg_features())
        example["totalFeatures"] = 2
        with self.assertRaises(ValueError):
            validate_snapshot(json.dumps(example).encode(), "DBS_EDIFICATO", bbox)

    def test_unreal_east_north_reflection_and_3d_removal(self):
        source = json.loads(mock_fvg_features())
        ids, polys = to_unreal_shapes(source, np.array([373390., 5113920., 200.]))
        self.assertEqual(ids, ["DBS_EDIFICATO.1"])
        self.assertEqual(polys[0].bounds, (10., 15., 15., 20.))
        self.assertFalse(shapely.has_z(polys[0]))

    def test_layer_comparison_not_automatic_wall_assignment(self):
        target = shapely.box(0, 0, 3, 3)
        shapes = np.asarray([shapely.box(1, 1, 4, 4),
                             shapely.box(20, 20, 22, 22)], dtype=object)
        ids = ["fvg.1", "fvg.2"]
        asphalt = shapely.box(.5, .5, 3.5, 2)
        chassis = shapely.box(2, 2, 3, 3)
        window = shapely.box(-5, -5, 5, 5)
        out = compare_layer(target, ids, shapes, asphalt, chassis, window)
        self.assertEqual(out["regional_ids_overlapping_osm_target"], ["fvg.1"])
        self.assertEqual(out["candidate_best_match_id"], "fvg.1")
        self.assertGreater(out["regional_union_asphalt_overlap_m2"], 1.)
        self.assertEqual(out["regional_features_touching_chassis"], 1)
        self.assertFalse(out["true_wall_assignment_verified"])

    def test_empty_regional_window(self):
        result = compare_layer(
            shapely.box(0, 0, 1, 1), ["far"],
            np.asarray([shapely.box(100, 100, 101, 101)], dtype=object),
            shapely.box(-1, -1, 2, 2), shapely.box(0, 0, 1, 1),
            shapely.box(-5, -5, 5, 5)
        )
        self.assertEqual(result["regional_union_chassis_overlap_m2"], 0.)
        self.assertIsNone(result["candidate_best_match_id"])

    def test_segment_runs_and_peak_report(self):
        self.assertEqual(segment_ranges([]), [])
        self.assertEqual(segment_ranges([4, 2, 3, 9, 9, 11]),
                         [[2, 4], [9, 9], [11, 11]])
        class Inverse:
            def transform(self, east, north):
                return east/1000., north/1000.
        pairs = np.asarray([[1, 2, 5], [0, 0, 1]])
        areas = np.asarray([.15, .21, 1.22])
        times = np.arange(8) / 2.
        positions = np.stack((np.arange(8), np.zeros(8), np.zeros(8)), axis=1)
        cases = summarize_hits(
            ["fvg.1", "fvg.2"], pairs, areas, times,
            positions, np.zeros(3), Inverse()
        )
        self.assertEqual(cases[0]["regional_id"], "fvg.2")
        self.assertEqual(cases[0]["interval_sequences"], [[2.5, 3.]])
        self.assertFalse(cases[0]["current_wall_collision_proven"])

    def test_hotspot_overview_synthetic_and_committed_figures(self):
        from xml.etree import ElementTree
        box = shapely.box(-8, -8, 8, 8)
        case = [{"ue_xy": [2, 3], "source_id": "fvg.1", "peak_overlap_m2": .5}]
        svg = render_overview(
            box, shapely.LineString([(-4, 0), (4, 0)]),
            {"way/36158219": box},
            {name:[box] for name in ("DBS_EDIFICATO", "EDIFICATO_CTRN_ED1_067",
                                   "EDIFICATO_CTRN_ED2_067")},
            case, center=(0, 0), radius=120
        )
        self.assertTrue(ElementTree.fromstring(svg).tag.endswith("svg"))
        self.assertIn("Regione FVG", svg)
        folder = Path(__file__).resolve().parents[1] / "docs/figure_fvg_mont_joanes"
        diagram = folder / "overview.svg"
        page = folder / "overview.html"
        self.assertTrue(ElementTree.parse(diagram).getroot().tag.endswith("svg"))
        self.assertIn("OpenStreetMap", diagram.read_text(encoding="utf-8"))
        self.assertIn("DBTsped", page.read_text(encoding="utf-8"))
        self.assertNotIn("<img ", page.read_text(encoding="utf-8"))

    def test_svg_source_identification(self):
        shape = shapely.box(-2, -2, 2, 2)
        case = {"osm_id": "way/36158219", "peak_center_UE_xy_m": [0, 0]}
        svg = draw_overlay(case, shape, shape, shape,
                           {key:[shape] for key in ("DBS_EDIFICATO",
                                "EDIFICATO_CTRN_ED1_067", "EDIFICATO_CTRN_ED2_067")},
                           [{"position_UE_xy_m": [0, 1]}])
        from xml.etree import ElementTree
        node = ElementTree.fromstring(svg)
        self.assertTrue(node.tag.endswith("svg"))
        self.assertIn("FVG EDIFICI", svg)
        self.assertIn("OSM contributors", svg)


if __name__ == "__main__":
    unittest.main()
