import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from coffa.session import Journey, RuleViolation, atomic_save


def at_valle():
    j = Journey()
    j.pass_gate("campeglio", 1)
    j.pass_gate("valle", 1)
    return j


def explore():
    j = at_valle()
    j.begin_dismount(0, True, True, 1)
    j.set_transition_progress(1)
    j.finish_dismount(True)
    return j


class SessionTests(unittest.TestCase):
    def test_complete_visit_and_lap(self):
        j = explore()
        self.assertFalse(j.can_drive)
        j.mark_visit(True)
        j.begin_mount(True, True, 0)
        j.set_transition_progress(1)
        j.finish_mount(True, True)
        self.assertTrue(j.can_drive)
        j.pass_gate("rientro", 1)
        j.finish(True)
        self.assertEqual(j.phase, "complete")

    def test_gate_order_and_reverse(self):
        for gate, dot in (("valle", 1), ("campeglio", -1), ("campeglio", float("nan"))):
            j = Journey()
            with self.assertRaises(RuleViolation):
                j.pass_gate(gate, dot)
            self.assertEqual(j.next_gate, 0)

    def test_stop_cannot_replace_visit(self):
        j = at_valle()
        with self.assertRaises(RuleViolation):
            j.pass_gate("rientro", 1)
        with self.assertRaises(RuleViolation):
            j.finish(True)

    def test_dismount_interlocks(self):
        for args in ((2, True, True, 1), (0, False, True, 1), (0, True, False, 1),
                     (0, True, True, 0.8), (float("nan"), True, True, 1)):
            j = at_valle()
            with self.assertRaises(RuleViolation):
                j.begin_dismount(*args)
            self.assertTrue(j.can_drive)

    def test_no_timer_only_teleport_completion(self):
        j = at_valle()
        j.begin_dismount(0, True, True, 1)
        with self.assertRaises(RuleViolation):
            j.finish_dismount(True)
        j.set_transition_progress(1)
        with self.assertRaises(RuleViolation):
            j.finish_dismount(False)

    def test_mass_is_never_duplicated_over_twenty_cycles(self):
        for _ in range(20):
            j = at_valle()
            j.begin_dismount(0, True, True, 1)
            for step in range(101):
                j.set_transition_progress(step / 100)
                for person in j.owners:
                    self.assertAlmostEqual(sum(j.mass_weights(person).values()), 1)
                    self.assertEqual(j.mass_weights(person), {"vehicle": 0, "world": 1})
                self.assertFalse(j.can_drive)
            j.finish_dismount(True)
            j.mark_visit(True)
            j.begin_mount(True, True, 0)
            for step in range(101):
                j.set_transition_progress(step / 100)
                self.assertAlmostEqual(sum(j.mass_weights("passenger").values()), 1)
                self.assertEqual(j.mass_weights("passenger"), {"vehicle": 0, "world": 1})
            with self.assertRaises(RuleViolation):
                j.finish_mount(True, False)
            j.finish_mount(True, True)
            self.assertEqual(j.mass_weights("passenger"), {"vehicle": 1, "world": 0})

    def test_rollback_progress_rejected(self):
        j = at_valle()
        j.begin_dismount(0, True, True, 1)
        j.set_transition_progress(0.7)
        with self.assertRaises(RuleViolation):
            j.set_transition_progress(0.4)

    def test_recovery_cannot_create_record(self):
        j = Journey()
        j.incident()
        j.recover()
        self.assertFalse(j.valid)
        self.assertEqual(j.next_gate, 0)

    def test_atomic_save_and_restore(self):
        j = explore()
        j.mark_visit(True)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "save.json"
            atomic_save(p, j)
            restored = Journey.restore(json.loads(p.read_text()))
            self.assertEqual(restored.snapshot(), j.snapshot())
            j.begin_mount(True, True, 0)
            before = p.read_bytes()
            with self.assertRaises(RuleViolation):
                atomic_save(p, j)
            self.assertEqual(p.read_bytes(), before)

    def test_corrupt_saves_rejected(self):
        data = explore().snapshot()
        cases = [{**data, "version": 99}, {**data, "phase": "mounting"},
                 {**data, "next_gate": 0}, {**data, "owners": {"driver": "vehicle", "passenger": "world"}},
                 {**data, "valid": "yes"}, {**data, "phase": "complete", "visited": False}]
        for item in cases:
            with self.assertRaises(RuleViolation):
                Journey.restore(item)


if __name__ == "__main__":
    unittest.main()
