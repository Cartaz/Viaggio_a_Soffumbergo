#!/usr/bin/env python3
"""Recompute design diagnostics from explicit, uncalibrated lab configuration."""
import json
from pathlib import Path
from coffa.physics import aggregate, stability

ROOT = Path(__file__).resolve().parents[1]


def main():
    config = json.loads((ROOT / "data/config/vehicle_lab.json").read_text())
    body = aggregate(config["components"])
    result = {"status": config["status"], "warning": config["warning"], **body,
              "rigid_static_diagnostics": stability(config["body"]["track_m"], body["com_m"]),
              "godot_inertia_note": "Prototype uses tensor diagonal only. Off-diagonal terms below are retained for later principal-axis integration; not silently discarded from design data.",
              "suspension_static_mean_compression_m": body["mass_kg"] * 9.81 / (4 * config["suspension"]["spring_n_m"])}
    destination = ROOT / "reports/design_diagnostics.json"
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
