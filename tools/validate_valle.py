"""Reproducible engine acceptance gate; nonzero exit OR engine errors fail the run.

Local outputs/logs are ignored; public report is prepared separately after review.
Optional --source rebuilds twice and compares the scene bytes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--godot', type=Path, required=True)
    parser.add_argument('--blender', type=Path)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    folder = ROOT/'build/valle_validation'
    folder.mkdir(parents=True, exist_ok=True)
    (ROOT/'build/.gdignore').touch()
    steps = []
    (folder/'validation_report.json').write_text('{"passed":false}\n', encoding='utf-8')

    def run(name, command):
        started = time.monotonic()
        result = subprocess.run([str(v) for v in command], cwd=ROOT, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=180)
        log = result.stdout + result.stderr
        (folder/(name+'.log')).write_text(log, encoding='utf-8')
        errors = bool(re.search(r'(^|\n)(SCRIPT ERROR:|ERROR:|Traceback|WARNING: ObjectDB)', log))
        step = {'name': name, 'exit_code': result.returncode,
                'seconds': round(time.monotonic()-started, 3), 'engine_errors': errors}
        steps.append(step)
        (folder/'validation_report.json').write_text(
            json.dumps({'passed': False, 'steps': steps}, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(step), flush=True)
        if result.returncode or errors:
            raise RuntimeError('Validation failed: '+name+'; inspect '+str(folder/(name+'.log')))

    run('python', [sys.executable, 'tools/check_project.py'])
    run('yaris_regression', [sys.executable, 'tools/check_yaris_asset.py'])
    gd_files = sorted(str(p.relative_to(ROOT)) for p in (ROOT/'godot').rglob('*.gd'))
    for name, extra in [('gdparse', []), ('gdformat', ['--check']), ('gdlint', [])]:
        program = shutil.which(name) or Path(sys.executable).parent/(name+('.exe' if sys.platform == 'win32' else ''))
        run(name, [program]+extra+gd_files)
    if args.source:
        command = [sys.executable, 'tools/build_valle_3d.py', '--source', args.source.resolve()]
        run('generate', command)
        first = (ROOT/'build/valle/valle_scene.json').read_bytes()
        run('regenerate', command)
        if first != (ROOT/'build/valle/valle_scene.json').read_bytes():
            raise RuntimeError('Generation is not deterministic')
    run('geometry', [sys.executable, 'tools/check_valle_3d.py', 'build/valle/valle_scene.json'])
    godot = [args.godot.resolve(), '--path', ROOT]
    run('godot_import', godot+['--headless', '--editor', '--quit'])
    run('godot_reference', godot+['--headless', '--script', 'res://godot/tests/reference_checks.gd'])
    run('godot_headless', godot+['--headless', '--script', 'res://godot/tests/valle_check.gd',
                               '--', '--output=build/valle_validation/headless'])
    run('godot_missing', godot+['--headless', '--script', 'res://godot/tests/valle_check.gd',
                              '--', '--valle-data=build/missing-test-scene.json', '--expect-missing',
                              '--output=build/valle_validation/missing'])
    if args.capture:
        run('godot_render', godot+['--script', 'res://godot/tests/valle_check.gd', '--', '--capture',
                                  '--output=build/valle_validation/render'])
    if args.blender:
        run('blender', [args.blender.resolve(), '--background', '--factory-startup',
                        '--python', 'tools/blender/build_valle.py', '--', '--overwrite'])
    report = {'scene_sha256': hashlib.sha256((ROOT/'build/valle/valle_scene.json').read_bytes()).hexdigest(),
              'steps': steps, 'passed': True}
    (folder/'validation_report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
