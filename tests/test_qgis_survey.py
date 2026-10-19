"""The QGIS staging exporter must not invent full-route geometry or altitudes."""
import json
from pathlib import Path
import tempfile
import unittest
from tools.build_qgis_survey import SOURCES, build, _coordinates


def feature(fid, kind, coords, tags=None):
    return {"type": "Feature", "id": fid, "properties": tags or {},
            "geometry": {"type": kind, "coordinates": coords}}


class QGISSopralluogoTests(unittest.TestCase):
    def test_layers_only_with_source_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for source, sector in SOURCES:
                features = []
                if sector == "V":
                    features.append(feature("V-OUTBOUND", "LineString", [[13.392, 46.159], [13.393, 46.157]]))
                    features.append(feature("CIR-VAL-15", "Point", [13.3926, 46.1588]))
                elif sector == "E":
                    features.append(feature("CIR-12", "Point", [13.3792, 46.1581]))
                elif sector == "C":
                    features.append(feature("C-OSM", "LineString", [[13.38, 46.14], [13.39, 46.15]]))
                elif sector == "VALLE_OSM_CONTEXT":
                    features.append(feature("way/123", "LineString", [[13.392, 46.156], [13.393, 46.157]]))
                    features.append(feature("way/456", "Polygon", [[[13.392, 46.156], [13.393, 46.156], [13.393, 46.157], [13.392, 46.156]]]))
                else:
                    features.append(feature(f"{sector}-SAMPLE", "Point", [13.38, 46.14]))
                destination = root / source
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
            manifest = build(root)
            self.assertFalse(manifest["continuous_loop_centerline"])
            self.assertIsNone(manifest["vertical_datum"])
            self.assertEqual(manifest["layer_feature_counts"], {
                "observation_anchors.geojson": 8,
                "road_centerlines_partial.geojson": 2,
                "valle_context_roads.geojson": 1,
                "valle_footprints.geojson": 1,
            })
            output = root / "build/qgis"
            d_anchors = [f for f in json.loads((output / "observation_anchors.geojson").read_text())["features"]
                         if f["properties"]["sector"] == "D"]
            self.assertEqual({f["properties"]["ref_id"] for f in d_anchors}, {"D-START", "D-END"})
            self.assertTrue(all(f["properties"]["metric_status"] == "PLANIMETRY_ONLY_NOT_SURVEYED"
                                for f in d_anchors))
            for filename in manifest["layer_feature_counts"]:
                for f in json.loads((output / filename).read_text())["features"]:
                    self.assertEqual(len(f["geometry"]["coordinates"]) if f["geometry"]["type"] == "Point" else 2, 2)
                    self.assertIn("origin_file", f["properties"])
                    self.assertEqual(f["properties"]["height_status"], "NOT_AVAILABLE")

    def test_rejects_z_and_invalid_geometry(self):
        with self.assertRaises(ValueError):
            _coordinates({"type": "Point", "coordinates": [13.39, 46.15, 100]})
        with self.assertRaises(ValueError):
            _coordinates({"type": "Point", "coordinates": [float("nan"), 46.15]})
        with self.assertRaises(ValueError):
            _coordinates({"type": "LineString", "coordinates": [[13.39, 46.15]]})


if __name__ == "__main__":
    unittest.main()
