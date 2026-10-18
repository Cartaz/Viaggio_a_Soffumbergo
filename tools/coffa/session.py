"""Reference state machine: authoritative semantics for the later in-engine visit.

Transition start requires parking. Completion belongs to animation/navigation
callbacks, never an elapsed timer. A single ownership ledger prevents duplicated
passenger mass while climbing. No halfway-transition save is supported.
"""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import tempfile


class RuleViolation(ValueError):
    pass


class Journey:
    VERSION = 1

    def __init__(self, gates=("campeglio", "valle", "rientro")):
        self.gates = tuple(gates)
        if len(self.gates) < 3 or len(set(self.gates)) != len(self.gates) or not all(self.gates):
            raise RuleViolation("Need unique nonempty gates: Campeglio, Valle, then return")
        self.phase = "outbound"
        self.next_gate = 0
        self.visited = False
        self.valid = True
        self.owners = {"driver": "vehicle", "passenger": "vehicle"}
        self.transition_progress = 0.0

    def _require(self, condition, message):
        if not condition:
            raise RuleViolation(message)

    def pass_gate(self, gate, direction_dot):
        self._require(math.isfinite(direction_dot), "Invalid direction")
        self._require(self.phase in ("outbound", "returning"), "Not driving")
        self._require(self.next_gate < len(self.gates), "All gates already crossed")
        self._require(direction_dot > 0 and gate == self.gates[self.next_gate], "Wrong gate or direction")
        if self.next_gate >= 2:
            self._require(self.visited, "Visit required before return gates")
        self.next_gate += 1

    def begin_dismount(self, speed, brake, in_parking, upright):
        self._require(self.phase == "outbound" and self.next_gate == 2, "Reach Valle first")
        self._require(all(math.isfinite(v) for v in (speed, upright)), "Invalid motion")
        self._require(abs(speed) < 0.1 and brake and in_parking and upright > 0.95,
                      "Park stopped, upright, with brake applied")
        # Transfer representation once, at the same pose/velocity. The later
        # engine adapter must preserve momentum and support forces through
        # contacts/joints; changing ownership must NOT make the weight vanish.
        self.owners = {"driver": "world", "passenger": "world"}
        self.phase = "dismounting"
        self.transition_progress = 0.0

    def set_transition_progress(self, progress):
        self._require(self.phase in ("dismounting", "mounting"), "No transition")
        self._require(math.isfinite(progress) and self.transition_progress <= progress <= 1,
                      "Nonmonotonic or invalid transition")
        self.transition_progress = progress

    def finish_dismount(self, both_on_ground):
        self._require(self.phase == "dismounting" and both_on_ground and
                      self.transition_progress == 1, "Wait for physical descent")
        self.owners = {"driver": "world", "passenger": "world"}
        self.phase = "exploring"

    def mark_visit(self, reached_borgo):
        self._require(self.phase == "exploring" and reached_borgo, "Enter verified village zone")
        self.visited = True

    def begin_mount(self, both_near_car, brake, speed):
        self._require(self.phase == "exploring" and self.visited and both_near_car and brake and
                      math.isfinite(speed) and abs(speed) < 0.1, "Return both mice to parked car")
        self.phase = "mounting"
        self.transition_progress = 0.0

    def finish_mount(self, driver_seated, passenger_in_nest):
        self._require(self.phase == "mounting" and self.transition_progress == 1 and
                      driver_seated and passenger_in_nest, "Both travel poses required")
        self.owners = {"driver": "vehicle", "passenger": "vehicle"}
        self.phase = "returning"

    @property
    def can_drive(self):
        return self.phase in ("outbound", "returning") and all(v == "vehicle" for v in self.owners.values())

    def mass_weights(self, person):
        """Exactly one physical mass owner. No fractional fictitious split.

        Independent climbers still exert weight on the vehicle via constraints
        and contacts. Ownership is not the fraction of weight supported by it.
        """
        self._require(person in self.owners, "Unknown occupant")
        world = float(self.owners[person] == "world")
        return {"vehicle": 1 - world, "world": world}

    def incident(self):
        self._require(self.can_drive, "This reference incident models driving only")
        self.valid = False
        self.phase = "incident"

    def recover(self):
        """Recovery resets visit/gates/poses, and cannot restore a valid run."""
        self.__init__(self.gates)
        self.valid = False

    def finish(self, correct_finish_direction):
        self._require(self.phase == "returning" and self.next_gate == len(self.gates) and
                      self.visited and self.can_drive and correct_finish_direction and self.valid,
                      "Incomplete, reversed or invalid lap")
        self.phase = "complete"

    def snapshot(self):
        self._require(self.phase not in ("dismounting", "mounting"), "No mid-transition save")
        return {"version": self.VERSION, "gates": list(self.gates), "phase": self.phase,
                "next_gate": self.next_gate, "visited": self.visited, "valid": self.valid,
                "owners": deepcopy(self.owners)}

    @classmethod
    def restore(cls, data):
        if data.get("version") != cls.VERSION:
            raise RuleViolation("Unsupported save version")
        obj = cls(data["gates"])
        phase = data["phase"]
        if phase not in ("outbound", "exploring", "returning", "incident", "complete"):
            raise RuleViolation("Invalid save phase")
        n = data["next_gate"]
        if type(n) is not int or not 0 <= n <= len(obj.gates):
            raise RuleViolation("Invalid gate count")
        if type(data["visited"]) is not bool or type(data["valid"]) is not bool:
            raise RuleViolation("Invalid flags")
        expected = {"driver": "world", "passenger": "world"} if phase == "exploring" else {
            "driver": "vehicle", "passenger": "vehicle"}
        if data["owners"] != expected:
            raise RuleViolation("Inconsistent mass owners")
        if phase == "outbound" and n > 2:
            raise RuleViolation("Skipped visit")
        if phase == "exploring" and n != 2:
            raise RuleViolation("Exploration before arrival")
        if phase in ("returning", "complete") and (n < 2 or not data["visited"]):
            raise RuleViolation("Return without visit")
        if phase == "complete" and (n != len(obj.gates) or not data["valid"]):
            raise RuleViolation("Invalid completion")
        if phase == "incident" and data["valid"]:
            raise RuleViolation("Incident cannot be valid")
        obj.phase, obj.next_gate = phase, n
        obj.visited, obj.valid, obj.owners = data["visited"], data["valid"], deepcopy(expected)
        return obj


def atomic_save(path, journey):
    """Write/flush/replace within one directory; old file survives failed serialization."""
    data = journey.snapshot()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                         prefix=target.name + ".", suffix=".tmp", delete=False) as f:
            tmp = f.name
            json.dump(data, f, ensure_ascii=False, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)
