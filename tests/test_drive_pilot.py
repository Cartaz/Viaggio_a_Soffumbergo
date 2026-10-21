"""Engineering surfaces must preserve provenance and remain distinct from surveys."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from build_drive_pilot import closest, smooth_profile, make_strip


class DrivePilotTests(unittest.TestCase):
    def test_linear_grade_preserved_including_endpoints(self):
        p = [[0,i*.1,-i] for i in range(31)]
        result = smooth_profile(p)
        np.testing.assert_allclose(result[:,1],np.array(p)[:,1]+.15,atol=1e-12)

    def test_nearest_station_clamps_at_end(self):
        distance,height = closest([[0,0,0],[0,5,-10]],np.array([3,0]),np.array([-5,-20]))
        np.testing.assert_allclose(distance,[3,10])
        np.testing.assert_allclose(height,[2.5,5])

    def test_repeated_horizontal_point_rejected(self):
        with self.assertRaises(ValueError):
            closest([[0,0,0],[0,2,0]],np.array([0]),np.array([0]))

    def test_surface_width_and_front_faces(self):
        v,t = make_strip([[0,0,0],[0,1,-10],[0,2,-20]],4.5)
        np.testing.assert_allclose(np.linalg.norm(np.array(v)[::2]-np.array(v)[1::2],axis=1),4.5)
        for face in np.array(v)[t]:
            self.assertLess(np.cross(face[1]-face[0],face[2]-face[0])[1],0)

    def test_invalid_width_rejected(self):
        for width in [0,-1,float('nan')]:
            with self.assertRaises(ValueError):
                make_strip([[0,0,0],[0,1,-10]],width)
