import copy
import hashlib
import json
import math
from pathlib import Path
import unittest
from urllib.parse import parse_qs, urlparse

from tools.coffa.environment import observation_code, parse_feature, recipe, validate_object

ROOT = Path(__file__).resolve().parents[1]


class EnvironmentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT/'data/geography/circuit_placeholders.json').read_bytes())

    def test_no_claim_of_continuous_or_metric_survey(self):
        c = self.catalog
        self.assertFalse(c['google_imagery_copied'])
        self.assertFalse(c['dimensions_inferred_from_perspective'])
        self.assertFalse(c['coverage']['continuous_visual_coverage_verified'])
        self.assertFalse(c['coverage']['individual_objects_exhaustively_surveyed'])
        self.assertTrue(c['coverage']['all_sectors_have_observed_stations'])
        self.assertEqual({r['sector'] for r in c['reviews']}, set('ABCVDEF'))
        self.assertEqual(len(c['reviews']), c['coverage']['review_count'])
        self.assertTrue(all(r['panorama_offset_from_target_m'] < 30 for r in c['reviews']))
        self.assertLess(c['coverage']['baseline_max_gap_m'], 270)

    def test_every_placeholder_has_complete_recipe_and_stable_identity(self):
        c = self.catalog
        seen = set()
        for obj in c['objects']:
            validate_object(obj)
            self.assertNotIn(obj['code'], seen)
            seen.add(obj['code'])
            self.assertIn(obj['category'], c['categories'])
            if 'osm_id' not in obj:
                pano = parse_qs(urlparse(obj['source'][0]['url']).query)['pano'][0]
                self.assertEqual(obj['code'], observation_code(pano, c['categories'][obj['category']]['code'], obj['bearing_deg']))
            self.assertEqual(obj['collision_enabled'], False)
            if obj['runtime_status'] == 'visible_blockout':
                self.assertGreater(obj['road_clearance_m'], c['protected_road_and_shoulder_margin_m']-.01)
        active = [code for codes in c['tiles'].values() for code in codes]
        self.assertEqual(len(active), len(set(active)))
        self.assertEqual(set(active), {o['code'] for o in c['objects'] if o['runtime_status'] == 'visible_blockout'})

    def test_source_fingerprints_match_committed_inputs(self):
        for relative, expected in self.catalog['fingerprints'].items():
            if relative in {'construction_manifest', 'shoulders_manifest'}:
                continue  # Local raster derivatives are deliberately absent on CI.
            raw = (ROOT/relative).read_bytes().replace(b'\r\n', b'\n')
            self.assertEqual(hashlib.sha256(raw).hexdigest(), expected, relative)

    def test_offline_catalog_embeds_exact_recipe_without_remote_media(self):
        page = (ROOT/'reports/CATALOGO_SEGNAPOSTO.html').read_text(encoding='utf-8')
        embedded = page.split('const data=', 1)[1].split(';const search=', 1)[0]
        self.assertEqual(json.loads(embedded), self.catalog)
        self.assertNotIn('<img', page)
        self.assertNotRegex(page, r'<script[^>]+src=')
        self.assertIn('textContent=o.description', page)

    def test_legacy_valle_ids_not_duplicated_and_conflicts_explicit(self):
        objects = self.catalog['objects']
        osm_ids = [o['osm_id'] for o in objects if 'osm_id' in o]
        self.assertEqual(len(osm_ids), len(set(osm_ids)))
        self.assertEqual(len(self.catalog['covered_legacy_osm_ids']), 91)
        self.assertTrue(set(self.catalog['covered_legacy_osm_ids']) <= set(osm_ids))
        bell = next(o for o in objects if o.get('osm_id') == 'way/36427963')
        self.assertEqual(bell['category'], 'tower')
        self.assertEqual({s['review_id'] for s in bell['source'] if s['kind'] == 'streetview_observation'}, {'SV-V03', 'SV-V04'})
        for o in objects:
            if o['runtime_status'] != 'visible_blockout':
                self.assertNotIn(o['code'], self.catalog['tiles'].get(o['tile_id'], []))
        # OSM context is never silently promoted to an identified Street View facade.
        self.assertTrue(all('not_individual' in r['status'] for r in self.catalog['building_context_links']))

    def test_recipes_are_deterministic_and_group_count_is_explicit(self):
        for category in self.catalog['categories'].values():
            self.assertEqual(recipe(category), recipe(category))
            self.assertTrue(all(min(p['size_m']) > 0 for p in recipe(category)))
        trees = recipe(self.catalog['categories']['woodland'])
        self.assertEqual(len(trees), 10)  # Five symbolic trees, not five observed trunks.
        self.assertEqual(observation_code('pano', 'TRE', 359), observation_code('pano', 'TRE', 1))
        self.assertNotEqual(observation_code('pano', 'TRE', 0), observation_code('pano', 'TRE', 180))

    def test_invalid_or_unsourced_guessed_geometry_is_rejected(self):
        sample = next(o for o in self.catalog['objects'] if o['category'] == 'woodland')
        for field, value in [('collision_enabled', True), ('source', []), ('description', ''),
                             ('position_m', [0, math.nan, 0]), ('dimensions_status', 'measured_from_photo')]:
            obj = copy.deepcopy(sample)
            obj[field] = value
            with self.assertRaises(ValueError, msg=field):
                validate_object(obj)
        obj = copy.deepcopy(sample)
        obj['primitives'][0]['size_m'][0] = -1
        with self.assertRaises(ValueError):
            validate_object(obj)
        self.assertEqual(parse_feature('wall:R@180', 0), ('wall', 'R', 180.0, 270.0))
        for text in ['wall:X', 'wall:R@999', 'wall:R;bad']:
            with self.assertRaises(ValueError):
                parse_feature(text, 0)


if __name__ == '__main__':
    unittest.main()
