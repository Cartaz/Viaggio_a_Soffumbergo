import io
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from catalog_circuit_dtm import read_header, overlap_slices, resolve_samples

HEADER = 'ncols 1800\nnrows 1680\nxllcenter 100.25\nyllcenter 200.25\ncellsize .5\nnodata_value -9999\n'


class CircuitDtmTests(unittest.TestCase):
    def test_header_centres_strict(self):
        self.assertEqual(read_header(io.StringIO(HEADER))['xllcenter'], 100.25)
        for text in [HEADER.replace('cellsize .5','cellsize 1'),
                     HEADER.replace('xllcenter 100.25','xllcorner 100'),
                     HEADER.replace('100.25','100.1'), HEADER.replace('100.25','nan')]:
            with self.assertRaises(ValueError):
                read_header(io.StringIO(text))

    def test_horizontal_overlap_windows(self):
        left, right = overlap_slices([0,0,900,840], [820,0,1720,840])
        self.assertEqual(left, (slice(0,1680),slice(1640,1800)))
        self.assertEqual(right, (slice(0,1680),slice(0,160)))

    def test_vertical_overlap_windows(self):
        top, bottom = overlap_slices([0,760,900,1600], [0,0,900,840])
        self.assertEqual(top, (slice(1520,1680),slice(0,1800)))
        self.assertEqual(bottom, (slice(0,160),slice(0,1800)))

    def test_disjoint_and_misaligned(self):
        self.assertIsNone(overlap_slices([0,0,900,840], [900,0,1800,840]))
        with self.assertRaises(ValueError):
            overlap_slices([0,0,900,840],[820.1,0,1720.1,840])

    def test_conflicts_are_not_averaged_or_hidden_by_priority(self):
        self.assertEqual(resolve_samples([]), (None, 'uncovered', None))
        self.assertEqual(resolve_samples([100,100]), (100, 'covered', 0))
        value, status, spread = resolve_samples([100,100.03])
        self.assertIsNone(value)
        self.assertEqual(status, 'conflicting_overlap')
        self.assertAlmostEqual(spread, .03)

    def test_received_catalog_counts_and_known_valle_hashes(self):
        root = Path(__file__).resolve().parents[1]
        catalog = json.loads((root/'data/geography/circuit_dtm_catalog_20261020.json').read_text())
        self.assertEqual(catalog['tile_count'], len(catalog['tiles']))
        self.assertEqual(sum(t['valid_cells'] for t in catalog['tiles']), 123984000)
        self.assertEqual(sum(t['nodata_cells'] for t in catalog['tiles']), 0)
        self.assertEqual(len({t['filename'] for t in catalog['tiles']}), 41)
        known = json.loads((root/'data/geography/lidar05_valle_tile_manifest_20261020.json').read_text())
        received = {t['filename']: t['sha256'] for t in catalog['tiles']}
        for tile in known['tiles']:
            self.assertEqual(received[tile['asc_member']], tile['asc_sha256'])
        self.assertFalse(catalog['mosaic_merge_performed'])
        self.assertTrue(catalog['route_ground_fully_covered_at_2m'])
        self.assertFalse(catalog['route_height_unambiguous_at_2m'])
        for sector in catalog['route_ground_coverage']:
            self.assertEqual(sector['samples_at_max_2m_spacing'],
                             sector['unambiguous_height_samples']+sector['conflicting_height_samples']+
                             sector['uncovered_samples'])
