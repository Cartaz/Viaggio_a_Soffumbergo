import json
import math
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from coffa.physics import aggregate, friction_circle, reachable, stability, suspension


class PhysicsTests(unittest.TestCase):
    def test_single_cube_analytic_inertia(self):
        a = aggregate([dict(id="cube", mass_kg=12, position_m=[0, 0, 0], box_m=[2, 2, 2])])
        self.assertEqual(a["inertia_kg_m2"], [[8, 0, 0], [0, 8, 0], [0, 0, 8]])

    def test_parallel_axis_known_two_cubes(self):
        parts = [dict(id=str(x), mass_kg=3, position_m=[x, 0, 0], box_m=[2, 2, 2]) for x in (-2, 2)]
        a = aggregate(parts)
        self.assertEqual(a["com_m"], [0, 0, 0])
        self.assertEqual(a["inertia_kg_m2"], [[4, 0, 0], [0, 28, 0], [0, 0, 28]])

    def test_tensor_is_translation_invariant_and_positive(self):
        rng = random.Random(894)
        parts = [dict(id=str(i), mass_kg=rng.uniform(1, 100),
                      position_m=[rng.uniform(-5, 5) for _ in range(3)], box_m=[1, 2, 3]) for i in range(20)]
        original = aggregate(parts)
        shifted = aggregate([{**p, "position_m": [v + 100 for v in p["position_m"]]} for p in parts])
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(original["inertia_kg_m2"][i][j], shifted["inertia_kg_m2"][i][j], places=7)
        for _ in range(100):
            v = [rng.uniform(-1, 1) for _ in range(3)]
            self.assertGreater(sum(v[i] * original["inertia_kg_m2"][i][j] * v[j]
                                   for i in range(3) for j in range(3)), 0)

    def test_bad_mass_and_duplicate_rejected(self):
        p = dict(id="a", mass_kg=1, position_m=[0, 1, 0], box_m=[1, 1, 1])
        for parts in ([], [p, p], [{**p, "mass_kg": float("nan")}], [{**p, "mass_kg": -1}]):
            with self.assertRaises(ValueError):
                aggregate(parts)

    def test_high_load_reduces_static_margin(self):
        low = stability(1.52, [0, 0.55, 0])
        high = stability(1.52, [0.1, 1.5, 0])
        self.assertLess(high["weak_side_a_over_g"], low["weak_side_a_over_g"])
        self.assertAlmostEqual(low["ssf_centered"], 1.52 / 1.1)
        self.assertLess(high["weak_side_a_over_g"], high["ssf_centered"])

    def test_combined_friction_budget_random_inputs(self):
        rng = random.Random(42)
        for _ in range(1000):
            fx, fy = rng.uniform(-20000, 20000), rng.uniform(-20000, 20000)
            n, mu = rng.uniform(0, 6000), rng.uniform(0.1, 1.2)
            x, y = friction_circle(fx, fy, n, mu)
            self.assertLessEqual(math.hypot(x, y), mu * n + 1e-8)
            self.assertGreaterEqual(x * fx + y * fy, 0)
        self.assertEqual(friction_circle(100, 100, 0, 1), (0, 0))

    def test_no_tensile_wheel_force(self):
        self.assertEqual(suspension(-0.1, -1, 32000, 3600), 0)
        self.assertEqual(suspension(0.1, 0, 32000, 3600), 3200)
        self.assertGreater(suspension(0.1, 1, 32000, 3600), 3200)

    def test_damper_removes_energy_at_several_steps(self):
        # Independent mass-spring bench: converges to analytic static sag m*g/k.
        sags = []
        for hz in (60, 120, 240):
            x, v, mass, k, c = 0.0, 0.0, 400, 32000, 3600
            dt = 1 / hz
            for _ in range(hz * 8):
                a = (mass * 9.81 - suspension(x, v, k, c)) / mass
                v += a * dt
                x += v * dt
            sags.append(x)
            self.assertAlmostEqual(x, mass * 9.81 / k, places=5)
            self.assertLess(abs(v), 1e-5)
        self.assertLess(max(sags) - min(sags), 1e-5)

    def test_no_anatomical_stretch(self):
        self.assertTrue(reachable(0.17, 0.1, 0.09))
        self.assertFalse(reachable(0.25, 0.1, 0.09))
        self.assertFalse(reachable(0.005, 0.1, 0.09))

    def test_configuration_is_explicitly_experimental(self):
        root = Path(__file__).resolve().parents[1]
        c = json.loads((root / "data/config/vehicle_lab.json").read_text())
        self.assertEqual(c["status"], "experimental_not_calibrated")
        result = aggregate(c["components"])
        self.assertAlmostEqual(result["mass_kg"], 1605)
        self.assertGreater(result["com_m"][1], 1.4)


if __name__ == "__main__":
    unittest.main()
