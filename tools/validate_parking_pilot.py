"""Run original drive regressions and the separate technical stop acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--godot', type=Path, required=True)
    parser.add_argument('--blender', type=Path)
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    out = ROOT/'build/parking_validation'
    out.mkdir(parents=True, exist_ok=True)
    steps = []
    report = out/'validation_report.json'

    def run(name, command):
        report.write_text(json.dumps({'passed': False, 'steps': steps}, indent=2)+'\n')
        start = time.monotonic()
        result = subprocess.run([str(s) for s in command], cwd=ROOT, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=600)
        log = result.stdout+result.stderr
        (out/(name+'.log')).write_text(log, encoding='utf-8')
        errors = bool(re.search(r'(^|\n)(SCRIPT ERROR:|ERROR:|Traceback|WARNING: ObjectDB)', log))
        step = {'name': name, 'exit_code': result.returncode, 'engine_errors': errors,
                'seconds': round(time.monotonic()-start, 3)}
        steps.append(step)
        print(json.dumps(step), flush=True)
        if result.returncode or errors:
            raise RuntimeError('Validation failed: '+name)

    command = [sys.executable, 'tools/validate_drive_pilot.py', '--godot', args.godot.resolve()]
    if args.capture:
        command.append('--capture')
    if args.blender:
        command += ['--blender', args.blender.resolve()]
    run('drive_regressions', command)
    originals = {n: (ROOT/'build/circuit'/n).read_bytes() for n in ['pilot_road.json', 'pilot_manifest.json', 'manifest.json']}
    run('generate', [sys.executable, 'tools/build_parking_pilot.py'])
    hashes = {n: hashlib.sha256((ROOT/'build/circuit'/n).read_bytes()).hexdigest() for n in ['parking_road.json', 'parking_manifest.json']}
    run('regenerate', [sys.executable, 'tools/build_parking_pilot.py'])
    assert all(hashlib.sha256((ROOT/'build/circuit'/n).read_bytes()).hexdigest() == h for n, h in hashes.items())
    assert all((ROOT/'build/circuit'/n).read_bytes() == b for n, b in originals.items())
    engine = [args.godot.resolve(), '--path', ROOT]
    run('parking_rules', engine+['--headless', '--script', 'godot/tests/parking_state_check.gd'])
    run('parking_headless', engine+['--headless', '--fixed-fps', '120', '--script', 'godot/tests/parking_pilot_check.gd', '--', '--fast-physics'])
    if args.capture:
        run('parking_render', engine+['--fixed-fps', '120', '--script', 'godot/tests/parking_pilot_check.gd', '--', '--capture'])
    if args.blender:
        run('parking_blender', [args.blender.resolve(), '--background', '--factory-startup', '--python', 'tools/blender/build_drive_pilot.py', '--', '--parking'])
    report.write_text(json.dumps({'passed': True, 'steps': steps, 'deterministic_files': hashes,
                                 'pilot_and_base_inputs_unchanged': True}, indent=2)+'\n')


if __name__ == '__main__':
    main()
