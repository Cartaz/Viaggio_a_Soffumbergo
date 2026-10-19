#!/usr/bin/env python3
"""Run preparation checks without importing bpy or invoking an engine."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    for p in (ROOT / "tools").rglob("*.py"):
        ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
    for p in list((ROOT / "data").rglob("*.json")) + list((ROOT / "data").rglob("*.geojson")):
        if ".raw." not in p.name:
            json.loads(p.read_text(encoding="utf-8"))
    for p in (ROOT / "reports").glob("*.svg"):
        ET.parse(p)
    for p in list((ROOT / "godot").rglob("*.gd")) + list((ROOT / "godot").rglob("*.tscn")) + [ROOT / "project.godot"]:
        for resource in re.findall(r'"res://([^"\n]+)"', p.read_text(encoding="utf-8")):
            # Engine tests create these ignored capture/report outputs on demand.
            # They are not committed input assets and are absent in a fresh clone.
            if p.parent == ROOT / "godot" / "tests" and resource.startswith(("art/source/generated/", "captures/")):
                continue
            if not (ROOT / resource).exists():
                raise ValueError(f"Missing resource {resource} in {p.relative_to(ROOT)}")
    before = {p: p.read_bytes() for p in (ROOT / "reports").iterdir() if p.suffix in (".json", ".svg", ".csv")}
    # Rebuild the deterministic derived artifacts and fail on drift.
    for script in ("design_report.py", "survey_report.py"):
        subprocess.run([sys.executable, str(ROOT / "tools" / script)], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL)
    for p, content in before.items():
        if content != p.read_bytes():
            raise ValueError("Generated report was stale: " + str(p.relative_to(ROOT)))
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT)
    if result.returncode:
        raise SystemExit(result.returncode)
    print("Preparation checks passed. Godot and Blender execution NOT performed.")


if __name__ == "__main__":
    main()
