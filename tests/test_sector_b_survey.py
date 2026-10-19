"""Guard against presenting the partial photographic survey as a completed road map."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from extract_sector_b import WAYPOINTS, extract, haversine


class SectorBTests(unittest.TestCase):
    def test_source_register_has_three_distinct_ordered_anchors(self):
        register = json.loads((ROOT / 'references/circuito/settore_b.json').read_text(encoding='utf-8'))
        geo = json.loads((ROOT / 'data/geography/sector_b_observations.geojson').read_text(encoding='utf-8'))
        self.assertEqual([f['id'] for f in geo['features']], ['CIR-06', 'CIR-07', 'CIR-08'])
        self.assertEqual([f['properties']['order'] for f in geo['features']], [7, 8, 9])
        self.assertEqual([tuple(f['geometry']['coordinates']) for f in geo['features']], list(WAYPOINTS))
        self.assertTrue(all(f['geometry']['type'] == 'Point' for f in geo['features']))
        self.assertFalse(register['drivable_mesh_ready'])
        self.assertIsNone(register['road_centerline'])
        self.assertIsNone(register['curve_count'])
        self.assertIsNone(register['continuous_visual_coverage_m'])
        self.assertEqual(sum(s['app_rounded_m'] for s in register['segments']), 2020)
        self.assertEqual([s['google_instruction_order'] for s in register['segments']], [7, 8])

    def test_haversine(self):
        self.assertEqual(haversine((13.3, 46.1), (13.3, 46.1)), 0)
        self.assertGreater(haversine(WAYPOINTS[0], WAYPOINTS[1]), 1100)

    def test_extract_synthetic_connected_road_only_candidate(self):
        mid1 = ((WAYPOINTS[0][0] + WAYPOINTS[1][0]) / 2,
                (WAYPOINTS[0][1] + WAYPOINTS[1][1]) / 2)
        roads = {'type': 'FeatureCollection', 'features': [
            {'geometry': {'type': 'LineString', 'coordinates': [WAYPOINTS[0], mid1, WAYPOINTS[1], WAYPOINTS[2]]},
             'properties': {'highway': 'unclassified'}},
            {'geometry': {'type': 'LineString', 'coordinates': [WAYPOINTS[1], (13.383, 46.132)]},
             'properties': {'highway': 'footway'}}]}
        result = extract(roads)
        feat = result['features'][0]
        self.assertFalse(feat['properties']['usable_as_road_mesh'])
        self.assertEqual(len(feat['geometry']['coordinates']), 4)
        self.assertEqual(feat['geometry']['coordinates'][0], list(WAYPOINTS[0]))
        self.assertEqual(feat['geometry']['coordinates'][-1], list(WAYPOINTS[-1]))
        self.assertEqual(feat['properties']['snap_distances_m'], [0, 0, 0])

    def test_incomplete_extract_refused(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            extract({'type': 'FeatureCollection', 'features': [
                {'geometry': {'type': 'LineString', 'coordinates': [WAYPOINTS[0], (13.367, 46.127)]},
                 'properties': {'highway': 'unclassified'}}]})

    def test_disconnected_extract_refused(self):
        roads = {'type': 'FeatureCollection', 'features': [
            {'geometry': {'type': 'LineString', 'coordinates': [WAYPOINTS[0], (13.367, 46.127)]},
             'properties': {'highway': 'unclassified'}},
            {'geometry': {'type': 'LineString', 'coordinates': [WAYPOINTS[1], WAYPOINTS[2]]},
             'properties': {'highway': 'unclassified'}}]}
        with self.assertRaisesRegex(ValueError, 'disconnected'):
            extract(roads)

    def test_private_or_footway_rejected(self):
        roads = {'type': 'FeatureCollection', 'features': [
            {'geometry': {'type': 'LineString', 'coordinates': list(WAYPOINTS)},
             'properties': {'highway': 'footway'}},
            {'geometry': {'type': 'LineString', 'coordinates': list(WAYPOINTS)},
             'properties': {'highway': 'residential', 'access': 'private'}}]}
        with self.assertRaisesRegex(ValueError, 'No car-eligible roads'):
            extract(roads)


if __name__ == '__main__':
    unittest.main()