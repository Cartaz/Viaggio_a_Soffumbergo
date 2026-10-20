"""Source choice, vectorized interpolation, holes and independent sector-edge sampling."""
import math
import json
from pathlib import Path
import sys
import unittest
import tempfile
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from coffa.dtm_mosaic import Mosaic, choose_source, corridor_sectors, masked_lod_error
from coffa.terrain import sample_grid
from build_circuit_3d import load_sources
from check_circuit_3d import check


class MosaicTests(unittest.TestCase):
    def test_priority_then_interior_then_filename_without_averaging(self):
        candidates = [('B',100.03,20,False),('A',100,10,False)]
        self.assertEqual(choose_source(candidates),candidates[0])
        self.assertEqual(choose_source(candidates+[('C',105,1,True)])[0],'C')
        self.assertEqual(choose_source([('B',2,10,False),('A',1,10,False)])[0],'A')
        self.assertIsNone(choose_source([]))

    def test_batch_matches_cell_centre_scalar_sampler(self):
        grid = np.array([[0,10],[20,30]],dtype=np.float32)
        mosaic = Mosaic([{'filename':'A','bounds_EN_m':[0,0,1,1]}],[grid],[0,1,0])
        xx,zz = np.meshgrid(np.linspace(.25,.75,7),np.linspace(.25,.75,7))
        height,source,spread = mosaic.sample(xx,zz)
        for index in np.ndindex(xx.shape):
            self.assertAlmostEqual(height[index],sample_grid(grid,xx[index],1-zz[index],0,1))
        self.assertTrue((source==0).all())
        self.assertTrue((spread==0).all())

    def test_vectorized_priority_and_source_spread_survive_input_reordering(self):
        tiles = [{'filename':'A','bounds_EN_m':[0,0,2,2]},
                 {'filename':'B','bounds_EN_m':[.5,0,2.5,2]}]
        arrays = [np.full((4,4),100,dtype=np.float32),np.full((4,4),100.03,dtype=np.float32)]
        m = Mosaic(tiles,arrays,[0,2,0])
        h,s,spread = m.sample([1.7],[1])
        self.assertEqual(s[0],1)
        self.assertEqual(h[0],float(arrays[1][0,0]))
        self.assertGreater(spread[0],.029)
        reordered = Mosaic(tiles[::-1],arrays[::-1],[0,2,0]).sample([1.7],[1])
        self.assertEqual(h.tolist(),reordered[0].tolist())
        pinned = Mosaic(tiles,arrays,[0,2,0],['A'],[-2,-2,4,4]).sample([1.7],[1])
        self.assertEqual(pinned[1][0],0)
        self.assertEqual(pinned[0][0],100)
        self.assertGreater(pinned[2][0],.029)

    def test_missing_or_nodata_has_no_source_and_no_filled_height(self):
        grid = np.array([[1,-9999],[3,4]],dtype=np.float32)
        m = Mosaic([{'filename':'A','bounds_EN_m':[0,0,1,1]}],[grid],[0,1,0])
        height,source,_ = m.sample([.5,2],[.5,.5])
        self.assertTrue(np.isnan(height).all())
        self.assertEqual(source.tolist(),[-1,-1])

    def test_same_world_coordinates_yield_identical_height_and_source_at_edges(self):
        grid = np.arange(36,dtype=np.float32).reshape(6,6)
        m = Mosaic([{'filename':'A','bounds_EN_m':[0,0,3,3]}],[grid],[0,3,0])
        left = m.sample([1.5],[1.25])
        right = m.sample(np.array([[1.5]]),np.array([[1.25]]))
        self.assertEqual(left[0][0],right[0][0,0])
        self.assertEqual(left[1][0],right[1][0,0])

    def test_masked_lod_does_not_turn_unknown_into_zero(self):
        grid = [float(r+c) for r in range(5) for c in range(5)]
        self.assertEqual(masked_lod_error(grid,5,2),0)
        grid[6] = None
        grid[12] += 8
        self.assertTrue(math.isfinite(masked_lod_error(grid,5,2)))
        self.assertIsNone(grid[6])

    def test_corridor_keeps_negative_coordinates_and_all_sampled_hairpin_legs(self):
        points = [[-1,0],[0,0],[127,0],[127,128],[122,128],[122,0]]
        selected = set(corridor_sectors(points,128,2))
        for x,z in points:
            self.assertIn((math.floor(x/128)*128,math.floor(z/128)*128),selected)
        self.assertNotIn((1024,1024),selected)

    def test_raw_source_change_rejected_before_parsing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'Ell_DTM_00000000.asc'
            path.write_bytes(b'changed source')
            with self.assertRaisesRegex(ValueError,'checksum changed'):
                load_sources(Path(folder),{'tiles':[{'filename':path.name,'sha256':'0'*64}]})

    def test_chunk_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path/'chunk.json').write_text('{}',encoding='utf-8')
            doc = {'axes':'+X east, +Y up, +Z south','datum_conversion_applied':False,
                   'road_surface_verified':False,'source_fingerprints':{},'source_tiles':[],
                   'sectors':[{'offset_xz_m':[0,0],'path':'chunk.json','sha256':'0'*64,'id':'0_0'}]}
            (path/'manifest.json').write_text(json.dumps(doc),encoding='utf-8')
            with self.assertRaisesRegex(AssertionError,'checksum mismatch'):
                check(path/'manifest.json')
