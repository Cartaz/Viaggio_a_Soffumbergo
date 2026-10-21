"""Run parking regressions, transfer invariants and actual dismount/walk/remount."""
import argparse
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
    out = ROOT/'build/visit_validation'
    out.mkdir(parents=True, exist_ok=True)
    steps = []
    report = out/'validation_report.json'
    report.write_text('{"passed":false}\n')

    def run(name, command):
        start = time.monotonic()
        result = subprocess.run([str(p) for p in command], cwd=ROOT, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=600)
        log = result.stdout+result.stderr
        (out/(name+'.log')).write_text(log, encoding='utf-8')
        errors = bool(re.search(r'(^|\n)(SCRIPT ERROR:|ERROR:|Traceback|WARNING: ObjectDB)', log))
        step = {'name': name, 'exit_code': result.returncode, 'engine_errors': errors,
                'seconds': round(time.monotonic()-start, 3)}
        steps.append(step)
        report.write_text(json.dumps({'passed': False, 'steps': steps}, indent=2)+'\n')
        print(json.dumps(step), flush=True)
        if result.returncode or errors:
            raise RuntimeError('Validation failed: '+name)

    command = [sys.executable, 'tools/validate_parking_pilot.py', '--godot', args.godot.resolve()]
    if args.blender:
        command += ['--blender', args.blender.resolve()]
    if args.capture:
        command.append('--capture')
    run('parking_regressions', command)
    engine = [args.godot.resolve(), '--path', ROOT]
    run('mass', engine+['--headless', '--script', 'godot/tests/visit_mass_check.gd'])
    for hz in [60, 120]:
        extra = ['--hz=60'] if hz == 60 else []
        run('visit_'+str(hz), engine+['--headless', '--fixed-fps', str(hz), '--script',
                                    'godot/tests/visit_pilot_check.gd', '--', '--fast-physics']+extra)
    if args.capture:
        run('visit_render', engine+['--fixed-fps', '120', '--script',
                                    'godot/tests/visit_pilot_check.gd', '--', '--capture'])
    report.write_text(json.dumps({'passed': True, 'steps': steps}, indent=2)+'\n')


if __name__ == '__main__':
    main()
