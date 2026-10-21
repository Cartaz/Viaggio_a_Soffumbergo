import json
from pathlib import Path
import sys
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from build_circuit_practice import sections


class PracticeTest(unittest.TestCase):
    def test_reversal_partitions_without_inventing_turning_circle(self):
        p = [[0, 0, 0], [100, 0, 0], [100, 0, 100], [100, 0, 0], [0, 0, 0]]
        stages, reversals = sections([{'sector':'A', 'points_m':p}], p)
        self.assertEqual(reversals, [0, 2])  # closure itself is a reversal in this synthetic example
        self.assertEqual(len(stages), 2)
        self.assertEqual(stages[0]['stop_reason'], 'unresolved_maneuver')
        self.assertEqual(stages[-1]['stop_reason'], 'unresolved_maneuver')
        self.assertEqual(stages[-1]['end_trim_m'], 18)
        for stage in stages:
            self.assertTrue(all(np.isfinite(stage['points_m']).ravel()))
            self.assertLess(stage['usable_station_range_m'][0], stage['usable_station_range_m'][1])
        self.assertAlmostEqual(sum(s['length_horizontal_m']+s['start_trim_m']+s['end_trim_m'] for s in stages), 400)

    def test_sector_boundary_and_interpolation_preserve_original_interior_points(self):
        p = [[0, 0, 0], [60, 6, 0], [60, 6, 60], [0, 0, 60], [0, 0, 0]]
        route = [{'sector':'B', 'points_m':p[:3]}, {'sector':'C', 'points_m':p[2:]}]
        stages, reversals = sections(route, p)
        self.assertEqual(reversals, [])
        self.assertEqual([s['id'] for s in stages], ['B1', 'C1'])
        self.assertEqual(stages[0]['points_m'][1], p[1])
        np.testing.assert_allclose(stages[0]['points_m'][0], [6, .6, 0])
        self.assertAlmostEqual(sum(s['length_horizontal_m'] for s in stages), 216)
        self.assertEqual(stages[0]['stop_reason'], 'practice_sector_boundary')

    def test_invalid_profile_fails(self):
        with self.assertRaises(ValueError):
            sections([{'sector':'A', 'points_m':[[0, 0, 0], [0, 0, 0]]}], [[0, 0, 0], [0, 0, 0]])

    def test_documentary_review_does_not_claim_field_maneuver_verification(self):
        review = json.loads((ROOT/'data/geography/circuit_maneuver_review.json').read_bytes())
        self.assertEqual(len(review['items']), 4)
        self.assertTrue(review['candidate_unchanged'])
        self.assertEqual(sum(i['classification'].startswith('documented_stop') for i in review['items']), 3)
        for item in review['items']:
            self.assertFalse(item['maneuver_space_verified'])
            self.assertTrue((ROOT/item['source']).is_file())


if __name__ == '__main__':
    unittest.main()
